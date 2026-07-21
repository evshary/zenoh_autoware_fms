# FMS dev stack — backend-aware orchestration.
#
#   just setup                  one-time first-run setup (slow; downloads several GB)
#   just up fms                 shared infra (sim + world + bridge + API + frontend)
#   just up vehicle <scope>     one vehicle (ego + Autoware; teleop attaches from the UI)
#   just down vehicle <scope>   tear down one vehicle
#   just down                   tear the whole stack down
#
# All backend-specific logic lives in backends/${BACKEND}.sh (default carla;
# override with BACKEND=<name>). See backends/README.md for the contract.
# `just setup` is idempotent — completed steps are detected and skipped.

# ── Shared bash prelude: helpers + backend resolution ──────────
# Interpolated verbatim into the orchestration recipes below via {{_lib}}.
# Defines the helper surface used by the recipes and by backends/<name>.sh:
#
#   msg / warn / die / have               output + checks
#   wait_for "label" timeout cmd          poll a command until success
#   run_steps "${STEPS[@]}"               run "Label:fn" entries, auto numbered
#   skip_if_present label check cmd       idempotent build pattern; cmd failure dies
#   valid_scope scope                     reject non-token vehicle scopes
#   plane_doctor                          flag stray zenoh-plane clients
#
# Variables: PROJECT_ROOT (repo root), BACKEND (env-overridable, default
# carla), BACKEND_NAME (set by the sourced backend script).
_lib := '''
PROJECT_ROOT="$FMS_ROOT"
BACKEND="${BACKEND:-carla}"
BACKEND_SCRIPT="${PROJECT_ROOT}/backends/${BACKEND}.sh"

msg()  { printf '%s\n' "$*"; }
warn() { printf 'WARN: %s\n'  "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }
# A vehicle scope becomes a container name + a zenoh key + a ROS namespace;
# this is the intersection those allow (no spaces / dots / dashes / leading digit).
valid_scope() { [[ "$1" =~ ^[a-zA-Z][a-zA-Z0-9_]*$ ]] || die "invalid scope '$1' (use [A-Za-z][A-Za-z0-9_]*)"; }

[ -f "$BACKEND_SCRIPT" ] || die "unknown BACKEND='$BACKEND'; available: $(
    ls "${PROJECT_ROOT}/backends/"*.sh 2>/dev/null \
        | xargs -n1 basename 2>/dev/null | sed 's/\.sh$//' | tr '\n' ' '
)"
# shellcheck source=/dev/null
source "$BACKEND_SCRIPT"

# wait_for: poll a command (run through eval, quote as one string) until it
# succeeds, with a timeout.  wait_for "API on :8000" 60 'curl -sf .../'
wait_for() {
    local label="$1" timeout="$2" cmd="$3" start=$SECONDS
    printf '  Waiting for %s... ' "$label"
    while [ $((SECONDS - start)) -lt "$timeout" ]; do
        if eval "$cmd" >/dev/null 2>&1; then
            printf 'ready (%ds)\n' "$((SECONDS - start))"
            return 0
        fi
        sleep 1
    done
    printf 'TIMEOUT after %ds\n' "$timeout"
    return 1
}

# run_steps: execute "Label:fn" entries with numbered banners. Total is
# derived from $#, so adding/removing a step renumbers automatically.
# Internal vars are _step_* prefixed because bash dynamic scoping lets a
# step's own `for i in ...` clobber a plainly-named `local` in this loop.
run_steps() {
    local _step_total=$# _step_idx=1 _step_label _step_fn _step_entry
    for _step_entry in "$@"; do
        _step_label="${_step_entry%%:*}"
        _step_fn="${_step_entry##*:}"
        printf '\n[%d/%d] %s\n' "$_step_idx" "$_step_total" "$_step_label"
        "$_step_fn" || die "step [$_step_idx/$_step_total] '$_step_label' failed"
        _step_idx=$((_step_idx + 1))
    done
}

# skip_if_present: run `cmd` only when `check` fails. Both run through eval.
# Dies on `cmd` failure: run_steps invokes steps as an `||` condition, which
# disables `set -e` in the whole call tree, so failures must be explicit here.
skip_if_present() {
    local label="$1" check="$2" cmd="$3"
    if eval "$check" >/dev/null 2>&1; then
        msg "  $label: already present — skipping"
    else
        msg "  $label: building..."
        eval "$cmd" || die "$label failed"
    fi
}

# plane_doctor: flag host processes on the zenoh planes (:7887 operator, :7447 sim,
# :7448+ per-vehicle) that aren't the stack's own — one wedged stray subscriber stalls
# routing for everyone. Container peers carry no pid here (root-owned). Returns 1 on strangers.
plane_doctor() {
    local api_pid ok_pids conns line pid comm stray=0
    api_pid="$(ss -Htlnp 'sport = :7887' 2>/dev/null | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2)"
    ok_pids=" ${api_pid:-none} $(pgrep -x zenoh_control 2>/dev/null | tr '\n' ' ')"
    conns="$(ss -Htnp state established 2>/dev/null \
        | awk '$3 ~ /:(7887|744[7-9]|74[5-9][0-9])$/ || $4 ~ /:(7887|744[7-9]|74[5-9][0-9])$/')"
    if [ -z "$conns" ]; then
        msg "  zenoh planes: no connections (stack down?)"
        return 0
    fi
    while IFS= read -r line; do
        case "$line" in *users:*) ;; *) continue ;; esac
        pid="$(printf '%s' "$line" | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2)"
        comm="$(printf '%s' "$line" | grep -oE '"[^"]+"' | head -1 | tr -d '"')"
        case "$ok_pids" in *" $pid "*) continue ;; esac
        warn "stray zenoh client: ${comm} (pid ${pid}) $(printf '%s' "$line" | awk '{print $3" <-> "$4}')"
        stray=1
    done <<PLANE_EOF
$conns
PLANE_EOF
    [ "$stray" = 0 ] && msg "  zenoh planes: stack members only"
    return "$stray"
}
'''

# api_server (uvicorn) + frontend (npm); invoked by `just up` under setsid
run:
    #!/usr/bin/env bash
    source env.sh
    # nvm's node may not be on a non-interactive shell's PATH (npm start needs it).
    for _nb in "$HOME"/.nvm/versions/node/*/bin; do [ -d "$_nb" ] && PATH="$_nb:$PATH"; done
    echo "API:      http://localhost:8000"
    echo "Frontend: http://localhost:3000"
    # `env -u PYTHONPATH`: prevent ROS-sourced shells from leaking system-Python
    # site-packages into uv's venv (lanelet2 ABI-incompatible build crashes import).
    # `--host 0.0.0.0`: bind all interfaces so the API is reachable across
    # Docker / SSH-forward boundaries, not just loopback.
    # `PYTHONUNBUFFERED`: stdout is a pipe; block-buffered prints would hide
    # supervision events from the live log.
    parallel --verbose --lb ::: \
        'env -u PYTHONPATH PYTHONUNBUFFERED=1 uv run uvicorn api_server:app --host 0.0.0.0 --port 8000 2>&1 | tee logs/api_server.log' \
        'cd frontend && npm start 2>&1 | tee logs/frontend.log'

# One-time first-run setup: host deps + build images/Rust/ROS + maps. Idempotent.
setup:
    #!/usr/bin/env bash
    set -e
    export FMS_ROOT='{{justfile_directory()}}'
    {{_lib}}
    # prerequisite.sh installs into dirs the current shell hasn't picked up yet:
    # colcon in ~/.local/bin, node under nvm's versioned dir.
    export PATH="$HOME/.local/bin:$PATH"
    for _nb in "$HOME"/.nvm/versions/node/*/bin; do [ -d "$_nb" ] && PATH="$_nb:$PATH"; done

    run_prerequisite() {
        bash "${PROJECT_ROOT}/prerequisite.sh"
    }
    check_host_tools() {
        for t in docker git uv node npm just colcon curl; do
            have "$t" || die "$t not in PATH"
        done
        backend_check_bootstrap_prereqs
    }
    init_submodules() {
        git -C "$PROJECT_ROOT" submodule update --init --recursive
    }

    build_fleet_teleop() {
        ( cd "$PROJECT_ROOT" && just build-teleop ) \
            || warn "build-teleop failed; fleet attach in zenoh mode will Error until it builds"
    }

    STEPS=(
        "Host prerequisites (prerequisite.sh):run_prerequisite"
        "Host tooling check:check_host_tools"
        "Init FMS submodules:init_submodules"
        "Backend artifacts (sim/bridge/Autoware):backend_bootstrap"
        "Operator-side fleet teleop (build-teleop):build_fleet_teleop"
        "Mirror backend assets to frontend/public:backend_seed_frontend_assets"
    )
    msg "═══ FMS Setup (backend: ${BACKEND_NAME}) ═══"
    run_steps "${STEPS[@]}"
    msg ""
    msg "═══ Setup complete ═══"
    msg "  Next: just up fms, then just up vehicle v1"

# Bring something up:
#   just up --ros            one vehicle the ROS way (single): sim + bridge + Autoware
#                            + in-container teleop; Autoware over DDS, no fleet, no scope
#   just up fms              shared infra: simulator + world + bridge + API + frontend
#   just up vehicle <scope>  one vehicle: ego + Autoware (teleop attaches from the UI)
up target scope="":
    #!/usr/bin/env bash
    set -e
    export FMS_ROOT='{{justfile_directory()}}'
    {{_lib}}
    mkdir -p "${PROJECT_ROOT}/logs"
    [ -f "${PROJECT_ROOT}/.env" ] && { set -a; source "${PROJECT_ROOT}/.env"; set +a; }

    cleanup_previous() {
        backend_stop > /dev/null 2>&1 || true
        pkill -9 -f "just run|uvicorn api_server|npm start" 2>/dev/null || true
        fuser -k 3000/tcp 8000/tcp 2>/dev/null || true
    }
    # Per-deployment overrides have to land between sim and bridge startup.
    start_simulator() {
        backend_start_sim
        backend_seed_custom_configs
    }
    start_fms_services() {
        backend_seed_frontend_assets

        if [ ! -x "${PROJECT_ROOT}/frontend/node_modules/.bin/react-scripts" ]; then
            msg "  react-scripts not installed — running npm install..."
            (cd "${PROJECT_ROOT}/frontend" && npm install 2>&1 | tail -5)
        fi

        # REACT_APP_* come from env.sh inside just run
        backend_export_runtime_flags

        # `setsid` puts the just-tree in its own PG (logs/just.pid) so
        # `just down` can `kill -- -PGID`. CHOKIDAR_USEPOLLING avoids inotify
        # ENOSPC; BROWSER=none keeps `npm start` SSH-friendly.
        BROWSER=none CHOKIDAR_USEPOLLING=true \
            nohup setsid just run > "${PROJECT_ROOT}/logs/run.log" 2>&1 &
        echo "$!" > "${PROJECT_ROOT}/logs/just.pid"

        wait_for "API on :8000"      60 'curl -sf http://localhost:8000/'
        wait_for "Frontend on :3000" 60 'curl -sf http://localhost:3000/'
    }

    _up_fms() {
        plane_check() {
            plane_doctor || warn "stray zenoh clients can wedge the plane — kill them (see just doctor)"
        }
        local STEPS=(
            "Cleanup previous instances:cleanup_previous"
            "Simulator (with per-deployment overrides):start_simulator"
            "Load sim world (once):backend_load_world"
            "Sim ↔ ROS bridge:backend_start_bridge"
            "FMS API + Frontend (via just run):start_fms_services"
            "Zenoh plane check:plane_check"
        )
        msg "═══ Starting FMS infra (backend: ${BACKEND_NAME}) ═══"
        backend_check_runtime_prereqs
        run_steps "${STEPS[@]}"
        msg ""
        msg "═══ FMS infra ready ═══"
        msg "  Frontend: http://localhost:3000    API: http://localhost:8000"
        msg "  Next: just up vehicle v1   (then just up vehicle v2, ... any scope)"
    }

    # in-container teleop over DDS; single-vehicle only (multivehicle stays zenoh-only)
    _up_ros() {
        export FMS_ROS_SINGLE=1
        start_ego() {
            backend_start_ego v1
        }
        start_manual_control() {
            local mc_dir="${PROJECT_ROOT}/external/autoware_manual_control"
            if [ ! -d "$mc_dir" ]; then
                msg "  manual_control submodule not present; skipping (FMS UI loads but intent has no listener)"
                return 0
            fi
            # FMS-owned config (Town01 presets, scope, modes) over the submodule seed.
            local cfg="${FMS_TELEOP_CONFIG:-${PROJECT_ROOT}/fms_teleop_config.yaml}"
            [ -f "$cfg" ] || cfg="${mc_dir}/config/teleop.example.yaml"
            backend_exec_in_ros "cd '${mc_dir}' && \
                colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release \
                    -DTELEOP_WITH_KEYBOARD=OFF -DTELEOP_WITH_ZENOH=ON" \
                || warn "manual_control build failed (backend container may not have source mounted)"
            msg "  Starting zenoh_control node..."
            backend_exec_in_ros -d "source '${mc_dir}/install/setup.bash' && \
                ros2 run autoware_manual_control zenoh_control --ros-args \
                    --params-file '${cfg}' \
                > /tmp/zenoh_control.log 2>&1"
            sleep 5  # let the node register subscribers before downstream connects
        }
        local STEPS=(
            "Cleanup previous instances:cleanup_previous"
            "Simulator (with per-deployment overrides):start_simulator"
            "Load sim world (once):backend_load_world"
            "Sim ↔ ROS bridge:backend_start_bridge"
            "Sim ego:start_ego"
            "Autoware ROS bringup:backend_start_autoware"
            "Manual control (build + launch):start_manual_control"
            "FMS API + Frontend (via just run):start_fms_services"
        )
        msg "═══ Starting FMS — single vehicle, ROS (backend: ${BACKEND_NAME}) ═══"
        backend_check_runtime_prereqs
        run_steps "${STEPS[@]}"
        msg ""
        msg "═══ Single-vehicle ROS stack ready ═══"
        msg "  Frontend: http://localhost:3000    API: http://localhost:8000"
        msg "  One vehicle, driven the ROS way (Autoware over DDS, in-container teleop)."
    }

    _up_vehicle() {
        export VEHICLE="$1"
        local STEPS=(
            "Sim ego (${VEHICLE}):backend_start_ego"
            "Autoware ROS bringup (${VEHICLE}):backend_start_autoware"
        )
        msg "═══ Starting vehicle ${VEHICLE} (backend: ${BACKEND_NAME}) ═══"
        backend_check_runtime_prereqs
        run_steps "${STEPS[@]}"
        msg ""
        msg "  Vehicle ${VEHICLE} up — select it in a browser tab to drive."
    }

    case "{{target}}" in
        --ros)   _up_ros ;;
        fms)     _up_fms ;;
        # {{scope}} is template-interpolated before bash runs: valid_scope guards consumers, not this expansion
        vehicle) [ -n "{{scope}}" ] || die "usage: just up vehicle <scope>"; valid_scope "{{scope}}"; _up_vehicle "{{scope}}" ;;
        *)       die "usage: just up [--ros | fms | vehicle <scope>]" ;;
    esac

# Tear something down:
#   just down                  everything (FMS services + backend + port orphans)
#   just down vehicle <scope>  one vehicle (its ego + Autoware + teleop); rest stay up
down target="" scope="":
    #!/usr/bin/env bash
    export FMS_ROOT='{{justfile_directory()}}'
    {{_lib}}

    _down_all() {
        pidfile="${PROJECT_ROOT}/logs/just.pid"
        msg "═══ Shutting down FMS (backend: ${BACKEND_NAME}) ═══"

        # Kill the FMS service group; skip a stale PGID equal to our own (self-kill).
        if [ -f "$pidfile" ]; then
            pgid=$(cat "$pidfile")
            own=$(ps -o pgid= -p $$ 2>/dev/null | tr -d ' ')
            if [ -n "$pgid" ] && [ "$pgid" != "$own" ] && kill -- -"$pgid" 2>/dev/null; then
                msg "Stopped FMS service tree (PG $pgid)"
            fi
            rm -f "$pidfile"
        fi

        backend_stop

        # Defensive: orphans on FMS-owned ports.
        for port in 3000 8000; do
            pids=$(lsof -ti :"$port" 2>/dev/null || true)
            if [ -n "$pids" ]; then
                kill $pids 2>/dev/null && msg "Killed orphans on :$port (pids: $pids)"
            fi
        done

        # Host-side fleet teleops; exact name so unrelated cmdlines never match.
        pkill -9 -x zenoh_control 2>/dev/null || true

        msg "═══ Stopped ═══"
    }

    case "{{target}}" in
        "")      _down_all ;;
        vehicle) [ -n "{{scope}}" ] || die "usage: just down vehicle <scope>"; valid_scope "{{scope}}"
                 # Detach via the api first: it stops the teleop AND clears the
                 # attached intent, so the supervision loop cannot respawn it.
                 # The pkill (exact per-scope config path) is the api-down fallback.
                 curl -sf -X POST "http://localhost:8000/fleet/detach?scope={{scope}}" >/dev/null 2>&1 \
                     || pkill -9 -f "zenoh_control --config ${PROJECT_ROOT}/tmp/fleet_teleop_{{scope}}\.yaml$" 2>/dev/null || true
                 backend_stop_vehicle "{{scope}}" ;;
        *)       die "usage: just down [vehicle <scope>]" ;;
    esac

# Build the native pure-zenoh teleop the fleet spawns (FLEET_TELEOP_BINARY); no ROS env needed
build-teleop:
    #!/usr/bin/env bash
    set -e
    # Clean PATH from Conda/miniforge to avoid python env pollution (catkin_pkg missing in conda)
    export PATH="$(echo "$PATH" | tr ':' '\n' | grep -v "miniforge3" | tr '\n' ':' | sed 's/:$//')"
    command -v colcon >/dev/null 2>&1 || { echo "ERROR: colcon not in PATH; run prerequisite.sh (installs it via \`uv tool install\`)" >&2; exit 1; }
    src="{{justfile_directory()}}/external/autoware_manual_control"
    ws="{{justfile_directory()}}/tmp/teleop-native-ws"
    [ -d "$src" ] || { echo "ERROR: teleop submodule missing at $src; run \`git submodule update --init\`" >&2; exit 1; }
    mkdir -p "$ws/src"
    ln -sfn "$src" "$ws/src/autoware_manual_control"
    BACKEND_ROOT="${BACKEND_ROOT:-{{justfile_directory()}}/../autoware_carla_launch}"
    ZENOH_VENDOR_PREFIX="${ZENOH_VENDOR_PREFIX:-${BACKEND_ROOT}/rmw_zenoh_ws/install/zenoh_cpp_vendor/opt/zenoh_cpp_vendor}"
    [ -d "$ZENOH_VENDOR_PREFIX/lib/cmake/zenohcxx" ] || { echo "ERROR: zenoh vendor not found at $ZENOH_VENDOR_PREFIX (set BACKEND_ROOT or ZENOH_VENDOR_PREFIX); run \`just setup\` (rmw_zenoh_ws zenoh_cpp_vendor step)" >&2; exit 1; }
    ZENOH_VENDOR_PREFIX="$(realpath "$ZENOH_VENDOR_PREFIX")"  # absolute, no .. so the baked RUNPATH is stable
    export ZENOH_VENDOR_PREFIX
    ( cd "$ws" && colcon build --merge-install --cmake-args \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_TESTING=OFF \
        -DTELEOP_WITH_KEYBOARD=OFF \
        -DTELEOP_WITH_ZENOH=ON \
        -DPython3_EXECUTABLE=/usr/bin/python3 \
        -DZENOH_VENDOR_PREFIX="${ZENOH_VENDOR_PREFIX}" \
        -DCMAKE_INSTALL_RPATH="${ZENOH_VENDOR_PREFIX}/lib" \
        -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
        -DTELEOP_AUTOWARE_TRANSPORT=native_zenoh )

# Flag stray host clients on the zenoh planes (one wedged subscriber stalls routing).
doctor:
    #!/usr/bin/env bash
    export FMS_ROOT='{{justfile_directory()}}'
    {{_lib}}
    plane_doctor

# Remove Python build artifacts (does NOT stop a running stack — use `just down`).
clean:
    rm -rf __pycache__ .venv
