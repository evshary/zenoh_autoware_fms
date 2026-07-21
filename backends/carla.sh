#!/usr/bin/env bash
#
# backends/carla.sh — Carla 0.9.14 + evshary/autoware_carla_launch backend
#
# Implements the contract in backends/README.md. Sourced by the justfile
# orchestration recipes (just up / down / setup) which provide the
# `msg`, `warn`, `die`, `have` helpers.

# ── Configuration ───────────────────────────────────────────

BACKEND_NAME="carla"

BACKEND_ROOT="${BACKEND_ROOT:-${PROJECT_ROOT}/../autoware_carla_launch}"
CARLA_BIN="${CARLA_BIN:-${PROJECT_ROOT}/../carla-0.9.14/CarlaUE4.sh}"

# Overridable so a fork can auto-clone from its own remote without editing this file.
CARLA_LAUNCH_URL="${CARLA_LAUNCH_URL:-https://github.com/evshary/autoware_carla_launch.git}"
CARLA_LAUNCH_BRANCH="${CARLA_LAUNCH_BRANCH:-main}"

BACKEND_BRIDGE_CONTAINER="zenoh_bridge"
BACKEND_AUTOWARE_CONTAINER="zenoh_autoware"
BACKEND_EGO_CONTAINER="zenoh_ego"

_CARLA_BRIDGE_IMAGE="zenoh-carla-bridge-1.5.0"
_AUTOWARE_RAW_IMAGE="zenoh-autoware-1.5.0"

_autoware_container() { printf '%s_%s' "$BACKEND_AUTOWARE_CONTAINER" "$1"; }
_ego_container()      { printf '%s_%s' "$BACKEND_EGO_CONTAINER" "$1"; }

# Lowest domain not claimed by a running vehicle (fms.domain label);
# freed automatically when the vehicle stops.
_alloc_domain() {
    local used n=1
    # not concurrent-safe: one up vehicle at a time
    used=$(docker ps -f label=fms.role=autoware --format '{{.Label "fms.domain"}}' 2>/dev/null)
    while printf '%s\n' "$used" | grep -qx "$n"; do n=$((n + 1)); done
    printf '%s' "$n"
}

# Inside-container path where rmw_zenoh's vendor prefix lives. autoware_manual_control's
# zenohcxx find_package() looks here at build time and at runtime.
_ZENOH_VP_INCONTAINER="/root/autoware_carla_launch/rmw_zenoh_ws/install/zenoh_cpp_vendor/opt/zenoh_cpp_vendor"

# Flags shared by every backend container: host net/ipc + privileged + memlock,
# plus the sibling tree mounted at the /root path upstream's env.sh expects.
_CARLA_COMMON=(--network host --privileged --ipc host --ulimit memlock=-1)
_CARLA_MOUNT=(-v "${BACKEND_ROOT}:/root/autoware_carla_launch" -w /root/autoware_carla_launch)

_carla_run() {
    local img="$1"; shift
    docker run --rm "${_CARLA_COMMON[@]}" "${_CARLA_MOUNT[@]}" \
        "$img" bash -c "$*"
}

# ── Prereq checks ───────────────────────────────────────────

backend_check_runtime_prereqs() {
    [ -d "$BACKEND_ROOT" ] || die "missing autoware_carla_launch sibling at $BACKEND_ROOT
  run \`just setup\` first; see backends/carla.md"
    [ -f "$BACKEND_ROOT/install/setup.bash" ] \
        || die "Autoware not built (no install/setup.bash) — run \`just setup\`"
    [ -x "$BACKEND_ROOT/external/zenoh_carla_bridge/target/release/zenoh_carla_bridge" ] \
        || die "Carla bridge binary not built — run \`just setup\`"
    docker image inspect "$_CARLA_BRIDGE_IMAGE" >/dev/null 2>&1 \
        || die "Docker image missing: $_CARLA_BRIDGE_IMAGE — run \`just setup\`"
    docker image inspect "$_AUTOWARE_RAW_IMAGE" >/dev/null 2>&1 \
        || die "Docker image missing: $_AUTOWARE_RAW_IMAGE — run \`just setup\`"
    # Missing Carla binary is non-fatal; backend_start_sim will skip with a warn.
}

backend_check_bootstrap_prereqs() {
    # Everything else is auto-installed by backend_bootstrap. The only
    # piece we don't auto-install by default is the Carla binary (~7 GB);
    # opt-in via CARLA_AUTODOWNLOAD=1.
    if [ ! -f "$CARLA_BIN" ] && [ "${CARLA_AUTODOWNLOAD:-0}" != "1" ]; then
        warn "Carla binary not at $CARLA_BIN — \`just up\` will skip sim startup.
  Set CARLA_AUTODOWNLOAD=1 to auto-download (~7 GB), or place an extracted
  CARLA_0.9.14 tree at $(dirname "$CARLA_BIN")/. See backends/carla.md."
    fi
}

# ── Asset seeding ───────────────────────────────────────────

# Ensure the frontend Map View's lanelet is in place, via the repo's own
# download_map.sh (the single canonical source; idempotent).
backend_seed_frontend_assets() {
    ( cd "$PROJECT_ROOT" && ./download_map.sh ) \
        || warn "map download failed — frontend Map View will be empty"
}

# Apply per-deployment speed-control overrides into the backend tree.
backend_seed_custom_configs() {
    [ -d "${PROJECT_ROOT}/autoware_configs/custom_control" ] || return 0
    [ -d "$BACKEND_ROOT" ] || return 0
    msg "  applying custom speed control configurations..."
    mkdir -p "${BACKEND_ROOT}/autoware_data/custom_control"
    cp -r "${PROJECT_ROOT}/autoware_configs/custom_control/"* \
          "${BACKEND_ROOT}/autoware_data/custom_control/"
}

# Backend-specific runtime env for the FMS services; carla needs none.
backend_export_runtime_flags() { :; }

# ── Lifecycle ───────────────────────────────────────────────

# Start Carla as a host process. `env -u DISPLAY` is required: UE4 4.26
# connects to X over SSH X11 forwarding even with -RenderOffScreen,
# blocking the main thread on do_poll().
backend_start_sim() {
    local i  # see run_steps in the justfile (dynamic scoping)
    if [ ! -f "$CARLA_BIN" ]; then
        warn "Carla binary not at $CARLA_BIN; skipping sim startup"
        return 0
    fi
    # A long-lived Carla degrades (5s RPC timeouts, stale actors) and then
    # silently breaks the engage handshake or spawns no ego vehicle, so
    # `just up` defaults to a deterministic restart: kill any running
    # Carla and start a known-good instance. Set CARLA_REUSE=1 to keep an
    # existing instance for fast iteration when it is known healthy.
    if [ "${CARLA_REUSE:-0}" = "1" ] && nc -z localhost 2000 2>/dev/null; then
        echo "  CARLA_REUSE=1 and :2000 open — reusing existing Carla (may be stale)."
        return 0
    fi
    if pgrep -f CarlaUE4 >/dev/null 2>&1; then
        echo "  Stopping existing Carla for a deterministic restart..."
        pkill -9 -f CarlaUE4 2>/dev/null
        fuser -k 2000/tcp 2>/dev/null || true
        for i in $(seq 1 15); do
            pgrep -f CarlaUE4 >/dev/null 2>&1 || break
            sleep 1
        done
    fi
    nohup env -u DISPLAY bash "$CARLA_BIN" -RenderOffScreen -nosound \
        > "${PROJECT_ROOT}/logs/carla.log" 2>&1 &
    echo -n "  Waiting for Carla on port 2000... "
    for i in $(seq 1 40); do
        nc -z localhost 2000 2>/dev/null && echo "port open." && break
        [ "$i" -eq 40 ] && echo "TIMEOUT." && return 1
        sleep 1
    done
    # Port 2000 opens before UE4 finishes loading the world. Bridge's
    # load_world() races and times out if it connects too early. Wait a
    # fixed duration; -RenderOffScreen's log doesn't reliably emit a
    # ready signal we could grep for.
    echo "  Giving Carla 15s to finish world load..."
    sleep 15
}

# Load the configured Carla world once. Per-vehicle agents then
# main.py --attach to it; if each loaded the world it would wipe the others.
backend_load_world() {
    [ -d "$BACKEND_ROOT" ] || { warn "skipping world load: backend root missing"; return 0; }
    docker run --rm --network host --privileged --ipc host \
        "${_CARLA_MOUNT[@]}" \
        "$_CARLA_BRIDGE_IMAGE" \
        bash -c 'source ./env.sh && cd external/zenoh_carla_bridge/carla_agent && \
            ./.venv/bin/python3 set_world.py "${CARLA_SIMULATOR_IP:-127.0.0.1}"'
}

# egos are spawned per-vehicle (backend_start_ego); the bridge discovers them dynamically
backend_start_bridge() {
    [ -d "$BACKEND_ROOT" ] || { warn "skipping bridge: backend root missing"; return 0; }
    docker rm -f "$BACKEND_BRIDGE_CONTAINER" >/dev/null 2>&1 || true
    docker run -d --name "$BACKEND_BRIDGE_CONTAINER" \
        "${_CARLA_COMMON[@]}" "${_CARLA_MOUNT[@]}" \
        "$_CARLA_BRIDGE_IMAGE" \
        bash -c 'source ./env.sh && \
            RUST_LOG=z=info "${AUTOWARE_CARLA_ROOT}/external/zenoh_carla_bridge/target/release/zenoh_carla_bridge" \
                --mode ros2 --zenoh-listen tcp/0.0.0.0:7447 \
                --zenoh-config ${ZENOH_CARLA_BRIDGE_CONFIG} --carla-address ${CARLA_SIMULATOR_IP}'
    echo "  Waiting 10s for bridge..."
    sleep 10
}

# --position random re-rolls until a spawn lands (a fixed pose retries forever on a
# blocked spot); --stop-signal=SIGINT so docker stop runs World.destroy, not orphaning actors
backend_start_ego() {
    [ -d "$BACKEND_ROOT" ] || { warn "skipping ego: backend root missing"; return 0; }
    local scope="${1:-${VEHICLE:?scope required}}" container
    container="$(_ego_container "$scope")"
    docker rm -f "$container" >/dev/null 2>&1 || true

    docker run -d --name "$container" --stop-signal=SIGINT \
        "${_CARLA_COMMON[@]}" \
        --label fms.role=ego --label fms.scope="$scope" \
        "${_CARLA_MOUNT[@]}" \
        "$_CARLA_BRIDGE_IMAGE" \
        bash -c "source ./env.sh && cd external/zenoh_carla_bridge/carla_agent && \
            ./.venv/bin/python3 main.py --attach --host \${CARLA_SIMULATOR_IP} --rolename ${scope} --position=random"
    echo "  Waiting 8s for ego (${scope})..."
    sleep 8
}

# GPU passthrough for the CUDA perception nodes. Probe each mechanism for
# real (a half-installed toolkit or a CDI spec stale after a driver bump
# still advertises itself): use the first that actually starts a container.
_GPU_LIB_DIR="${_GPU_LIB_DIR:-/usr/lib/x86_64-linux-gnu}"
_gpu_args() {
    if docker run --rm --gpus all "$_AUTOWARE_RAW_IMAGE" true >/dev/null 2>&1; then
        printf -- '--gpus all'; return 0
    fi
    if docker run --rm --device nvidia.com/gpu=all "$_AUTOWARE_RAW_IMAGE" true >/dev/null 2>&1; then
        printf -- '--device nvidia.com/gpu=all'; return 0
    fi
    [ -e /dev/nvidiactl ] || return 1
    local args="" d base f soname
    for d in /dev/nvidia0 /dev/nvidiactl /dev/nvidia-modeset \
             /dev/nvidia-uvm /dev/nvidia-uvm-tools; do
        [ -e "$d" ] && args="$args --device $d"
    done
    for base in libcuda libnvidia-ml libnvidia-ptxjitcompiler libnvidia-nvvm; do
        # only the real versioned file: prior installs leave stale dirs + symlinks
        f=$(ls -1 "${_GPU_LIB_DIR}/${base}".so.*.* 2>/dev/null | while read -r c; do
                [ -f "$c" ] && { echo "$c"; break; }
            done)
        [ -n "$f" ] || return 1
        case "$base" in
            libnvidia-nvvm) soname="${base}.so.4" ;;
            *)              soname="${base}.so.1" ;;
        esac
        args="$args -v ${f}:${_GPU_LIB_DIR}/${soname}:ro"
    done
    printf -- '%s' "$args"
}

# Same-path mount of the FMS repo so manual_control's in-container source
# paths match. Perception is always on and its CUDA nodes gate the drive
# path, so a GPU-less container can't drive — missing passthrough is fatal.
backend_start_autoware() {
    [ -d "$BACKEND_ROOT" ] || { warn "skipping autoware: backend root missing"; return 0; }
    local vehicle="${VEHICLE:-v1}" container domain port gpu ldpfx=""
    container="$(_autoware_container "$vehicle")"
    domain="$(_alloc_domain)"
    port=$((7448 + domain))  # = fleet_manager BRIDGE_PORT_BASE + domain
    gpu="$(_gpu_args)" || die "no working GPU passthrough for perception — need an NVIDIA driver plus one of: docker --gpus (nvidia container toolkit), CDI (--device nvidia.com/gpu=all), or visible /dev/nvidia* devices"
    case "$gpu" in *libcuda*) ldpfx="ldconfig 2>/dev/null; " ;; esac
    mkdir -p "${PROJECT_ROOT}/tmp"
    sed "s/__LISTEN_PORT__/${port}/" \
        "${PROJECT_ROOT}/backends/zenoh-bridge-ros2dds-conf.json5" \
        > "${PROJECT_ROOT}/tmp/bridge_${vehicle}.json5"
    docker rm -f "$container" >/dev/null 2>&1 || true
    docker run -d --name "$container" \
        "${_CARLA_COMMON[@]}" $gpu \
        --label fms.role=autoware --label fms.scope="$vehicle" --label fms.domain="$domain" \
        -v "${PROJECT_ROOT}:${PROJECT_ROOT}" \
        -v "${PROJECT_ROOT}/tmp:/fms_tmp:ro" \
        "${_CARLA_MOUNT[@]}" \
        "$_AUTOWARE_RAW_IMAGE" \
        bash -c "${ldpfx}source install/setup.bash && source env.sh && \
                 export ROS_DOMAIN_ID=${domain} && \
                 export ZENOH_BRIDGE_ROS2DDS_CONFIG=/fms_tmp/bridge_${vehicle}.json5 && \
                 ./script/autoware_ros2dds/run-autoware.sh ${vehicle} 127.0.0.1:7447 127.0.0.1:7887"
    # read back when the fleet targets each vehicle's bridge
    if [ -f "${PROJECT_ROOT}/tmp/vehicle_domains.env" ]; then
        sed -i "/^${vehicle}=/d" "${PROJECT_ROOT}/tmp/vehicle_domains.env"
    fi
    echo "${vehicle}=${domain}" >> "${PROJECT_ROOT}/tmp/vehicle_domains.env"
    echo "  Waiting 20s for Autoware stack (${vehicle}, domain ${domain})..."
    sleep 20
}

# Run a command in the backend's Autoware ROS environment. Sources
# /opt/autoware/setup.bash + autoware_carla_launch/env.sh + sets
# ZENOH_VENDOR_PREFIX and LD_LIBRARY_PATH so zenohcxx is reachable for
# both build (find_package) and run (dynamic linking). docker exec starts a
# fresh environment (env.sh then defaults ROS_DOMAIN_ID to 0), so re-pin it to
# this vehicle's domain (read back from the container's fms.domain label) or
# the teleop lands in the wrong Autoware.
#
# Usage:  backend_exec_in_ros 'cd ... && colcon build ...'
#         backend_exec_in_ros -d 'ros2 run ... > /tmp/log 2>&1'
backend_exec_in_ros() {
    local exec_opts="" container domain
    if [ "$1" = "-d" ]; then
        exec_opts="-d"
        shift
    fi
    container="$(_autoware_container "${VEHICLE:-v1}")"
    domain="$(docker inspect -f '{{index .Config.Labels "fms.domain"}}' "$container" 2>/dev/null)"
    docker exec $exec_opts "$container" bash -c \
        "export ZENOH_VENDOR_PREFIX=${_ZENOH_VP_INCONTAINER} && \
         export LD_LIBRARY_PATH=\${ZENOH_VENDOR_PREFIX}/lib:\${LD_LIBRARY_PATH:-} && \
         source /opt/autoware/setup.bash && \
         source /root/autoware_carla_launch/env.sh && \
         export ROS_DOMAIN_ID=${domain} && \
         $*"
}

# ── Shutdown ────────────────────────────────────────────────

backend_stop() {
    local stopped_any=0 c
    # name= is a substring match: also catches per-vehicle zenoh_autoware_v1/_v2
    for c in $(docker ps -aq -f "name=$BACKEND_AUTOWARE_CONTAINER" 2>/dev/null) \
             $(docker ps -aq -f "name=$BACKEND_EGO_CONTAINER" 2>/dev/null) \
             $(docker ps -aq -f "name=$BACKEND_BRIDGE_CONTAINER" 2>/dev/null); do
        echo "[backend:carla] Stopping container: $(docker inspect -f '{{.Name}}' "$c" 2>/dev/null)"
        docker rm -f "$c" >/dev/null 2>&1
        stopped_any=1
    done
    # force-kill: a degraded Carla (up, RPC port dead) ignores SIGTERM
    if [ "${CARLA_REUSE:-0}" != "1" ]; then
        if pkill -9 -f CarlaUE4 2>/dev/null; then
            echo "[backend:carla] Stopped Carla."
            stopped_any=1
        fi
        fuser -k 2000/tcp 2>/dev/null || true
    fi
    # Carla & bridge port cleanup. FMS ports (3000, 8000) are owned by the
    # `just down` recipe and cleaned up there.
    fuser -k 7447/tcp 7887/tcp 8080/tcp 2>/dev/null || true
    rm -f "${PROJECT_ROOT}/tmp/vehicle_domains.env"
    return 0
}

# Stop one vehicle, leaving others + shared sim/bridge up (just down vehicle stops the
# host-side teleop); ego via docker stop = SIGINT -> World.destroy (see backend_start_ego)
backend_stop_vehicle() {
    local scope="${1:-${VEHICLE:-v1}}" a e
    a="$(_autoware_container "$scope")"
    e="$(_ego_container "$scope")"
    docker rm -f "$a" >/dev/null 2>&1 || true
    if docker ps -q -f "name=^${e}$" 2>/dev/null | grep -q .; then
        docker stop "$e" >/dev/null 2>&1 || true
    fi
    docker rm -f "$e" >/dev/null 2>&1 || true
    if [ -f "${PROJECT_ROOT}/tmp/vehicle_domains.env" ]; then
        sed -i "/^${scope}=/d" "${PROJECT_ROOT}/tmp/vehicle_domains.env"
    fi
    echo "[backend:carla] Stopped vehicle: $scope"
}

# ── Bootstrap (one-time first-run build) ────────────────────

backend_bootstrap() {
    # An empty dir from a partial earlier clone blocks re-cloning; rmdir it first.
    if [ ! -d "$BACKEND_ROOT" ] || [ -z "$(ls -A "$BACKEND_ROOT" 2>/dev/null)" ]; then
        [ -d "$BACKEND_ROOT" ] && rmdir "$BACKEND_ROOT" 2>/dev/null
        msg "  cloning $CARLA_LAUNCH_URL (branch: $CARLA_LAUNCH_BRANCH)"
        git clone --recurse-submodules -b "$CARLA_LAUNCH_BRANCH" \
            "$CARLA_LAUNCH_URL" "$BACKEND_ROOT" \
            || die "autoware_carla_launch clone failed"
    else
        msg "  autoware_carla_launch sibling: already present — skipping clone"
    fi

    msg "  init backend submodules"
    git -C "$BACKEND_ROOT" submodule update --init --recursive \
        || die "backend submodule init failed"

    # Upstream's container/ scripts wrap the same docker build but then
    # exec rocker (an interactive shell), so build directly.
    skip_if_present "$_CARLA_BRIDGE_IMAGE Docker image" \
        "docker image inspect '$_CARLA_BRIDGE_IMAGE'" \
        "cd '$BACKEND_ROOT' && docker build -f container/Dockerfile_carla_bridge -t '$_CARLA_BRIDGE_IMAGE' ."

    skip_if_present "$_AUTOWARE_RAW_IMAGE Docker image" \
        "docker image inspect '$_AUTOWARE_RAW_IMAGE'" \
        "cd '$BACKEND_ROOT' && docker build -f container/Dockerfile_autoware -t '$_AUTOWARE_RAW_IMAGE' ."

    # Opt-in (CARLA_AUTODOWNLOAD=1) because it's a ~7 GB pull and the
    # user may already have it positioned.
    if [ ! -f "$CARLA_BIN" ] && [ "${CARLA_AUTODOWNLOAD:-0}" = "1" ]; then
        local carla_dir tarball url
        carla_dir="$(dirname "$CARLA_BIN")"
        tarball="${carla_dir}/CARLA_0.9.14.tar.gz"
        url="https://carla-releases.s3.us-east-005.backblazeb2.com/Linux/CARLA_0.9.14.tar.gz"
        msg "  downloading Carla 0.9.14 (~7 GB) to $carla_dir"
        mkdir -p "$carla_dir"
        if have wget; then
            wget --continue -O "$tarball" "$url" || die "Carla download failed"
        elif have curl; then
            curl -fL -C - -o "$tarball" "$url" || die "Carla download failed"
        else
            die "neither wget nor curl available — install one to use CARLA_AUTODOWNLOAD"
        fi
        tar xzf "$tarball" -C "$carla_dir" || die "Carla extraction failed"
        rm -f "$tarball"
        [ -f "$CARLA_BIN" ] || die "Carla extraction did not produce $CARLA_BIN"
    fi

    # Probe `cargo` (real binary) — symlinks may point at a container-only path.
    skip_if_present "Rust toolchain (carla bridge)" \
        "[ -x '${BACKEND_ROOT}/rust/bin/cargo' ]" \
        "_carla_run '$_CARLA_BRIDGE_IMAGE' \
            'source env.sh && ./script/setup/dependency_install.sh rust'"

    skip_if_present "zenoh_carla_bridge binary" \
        "[ -x '${BACKEND_ROOT}/external/zenoh_carla_bridge/target/release/zenoh_carla_bridge' ]" \
        "_carla_run '$_CARLA_BRIDGE_IMAGE' \
            'source env.sh && cd external/zenoh_carla_bridge && \
             CARLA_VERSION=0.9.14 cargo build --release'"

    # run-autoware.sh hard-requires this binary; upstream never builds it.
    skip_if_present "zenoh-bridge-ros2dds binary" \
        "[ -x '${BACKEND_ROOT}/external/zenoh-plugin-ros2dds/target/release/zenoh-bridge-ros2dds' ]" \
        "_carla_run '$_CARLA_BRIDGE_IMAGE' \
            'source env.sh && cd external/zenoh-plugin-ros2dds && \
             cargo build --release -p zenoh-bridge-ros2dds'"

    # poetry/pyenv installed into ${BACKEND_ROOT}/{poetry,pyenv}/.
    # Probe the venv binary, not bin/poetry which is an absolute
    # symlink to the in-container path.
    # Pin virtualenv <21 before poetry install: >=21 dropped the Python 3.8
    # seed wheels the sibling's pyenv 3.8.10 venvs need.
    skip_if_present "poetry / pyenv (host installs)" \
        "[ -x '${BACKEND_ROOT}/poetry/venv/bin/poetry' ]" \
        "_carla_run '$_CARLA_BRIDGE_IMAGE' \
            'source env.sh && mkdir -p \${POETRY_HOME} && \
             curl -sSL https://install.python-poetry.org | python3 - && \
             \${POETRY_HOME}/venv/bin/pip install -q \"virtualenv<21\" && \
             ./script/setup/dependency_install.sh python'"

    # Probe the carla package, not pyvenv.cfg: the upstream dependency script's
    # `poetry env use` pre-creates an EMPTY in-project venv.
    skip_if_present "carla_agent poetry venv" \
        "ls -d '${BACKEND_ROOT}/external/zenoh_carla_bridge/carla_agent/.venv/lib/'python*'/site-packages/carla'" \
        "_carla_run '$_CARLA_BRIDGE_IMAGE' \
            'source env.sh && poetry config virtualenvs.in-project true && \
             cd external/zenoh_carla_bridge/carla_agent && poetry install --no-root'"

    skip_if_present "Town01 map + perception models" \
        "[ -f '${BACKEND_ROOT}/carla_map/Town01/lanelet2_map.osm' ] && \
         [ -f '${BACKEND_ROOT}/carla_map/Town01/pointcloud_map.pcd' ]" \
        "_carla_run '$_AUTOWARE_RAW_IMAGE' \
            'source env.sh && \
             ./script/setup/download_map.sh && ./script/setup/download_models.sh'"

    skip_if_present "Autoware ROS workspace (colcon build)" \
        "[ -f '${BACKEND_ROOT}/install/setup.bash' ]" \
        "_carla_run '$_AUTOWARE_RAW_IMAGE' \
            'source /opt/autoware/setup.bash && source env.sh && \
             colcon build --symlink-install --base-paths src \
                 --cmake-args -DCMAKE_BUILD_TYPE=Release'"

    # zenohcxx for the teleop builds; only the vendor package, not full rmw_zenoh
    skip_if_present "rmw_zenoh_ws zenoh_cpp_vendor (zenohcxx)" \
        "[ -d '${BACKEND_ROOT}/rmw_zenoh_ws/install/zenoh_cpp_vendor/opt/zenoh_cpp_vendor/lib/cmake/zenohcxx' ]" \
        "_carla_run '$_CARLA_BRIDGE_IMAGE' \
            'source env.sh && mkdir -p rmw_zenoh_ws/src && \
             [ -d rmw_zenoh_ws/src/rmw_zenoh ] || \
                 git clone -b humble https://github.com/ros2/rmw_zenoh.git rmw_zenoh_ws/src/rmw_zenoh && \
             source /opt/ros/humble/setup.bash && cd rmw_zenoh_ws && \
             colcon build --packages-up-to zenoh_cpp_vendor \
                 --cmake-args -DCMAKE_BUILD_TYPE=Release'"
}
