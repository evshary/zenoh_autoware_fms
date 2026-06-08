# FMS dev stack — backend-aware orchestration.
#
#   just setup   one-time first-run setup (slow; downloads several GB)
#   just up       bring the stack up
#   just down     tear the stack down
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
#   skip_if_present label check cmd       idempotent build pattern
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
skip_if_present() {
    local label="$1" check="$2" cmd="$3"
    if eval "$check" >/dev/null 2>&1; then
        msg "  $label: already present — skipping"
    else
        msg "  $label: building..."
        eval "$cmd"
    fi
}
'''

# FMS web + API server only (backend started separately); rmw_zenoh variant
run_rmw_zenoh:
    USE_BRIDGE_ROS2DDS=False just run

# FMS web + API server only (backend started separately); ros2dds variant
run_ros2dds:
    USE_BRIDGE_ROS2DDS=True just run

# api_server (uvicorn) + frontend (npm); invoked by `just up` under setsid
run:
    #!/usr/bin/env bash
    source env.sh
    echo "API:      http://localhost:8000"
    echo "Frontend: http://localhost:3000"
    # `env -u PYTHONPATH`: prevent ROS-sourced shells from leaking system-Python
    # site-packages into uv's venv (lanelet2 ABI-incompatible build crashes import).
    # `--host 0.0.0.0`: bind all interfaces so the API is reachable across
    # Docker / SSH-forward boundaries, not just loopback.
    parallel --verbose --lb ::: \
        'env -u PYTHONPATH uv run uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload 2>&1 | tee logs/api_server.log' \
        'cd frontend && npm start 2>&1 | tee logs/frontend.log'

# One-time first-run setup: host deps + build images/Rust/ROS + maps. Idempotent.
setup:
    #!/usr/bin/env bash
    set -e
    export FMS_ROOT='{{justfile_directory()}}'
    {{_lib}}

    run_prerequisite() {
        # Host packages + uv sync + node/npm + map — delegated to prerequisite.sh.
        bash "${PROJECT_ROOT}/prerequisite.sh"
    }
    check_host_tools() {
        for t in docker git uv node npm just; do
            have "$t" || die "$t not in PATH"
        done
        backend_check_bootstrap_prereqs
    }
    init_submodules() {
        git -C "$PROJECT_ROOT" submodule update --init --recursive
    }

    STEPS=(
        "Host prerequisites (prerequisite.sh):run_prerequisite"
        "Host tooling check:check_host_tools"
        "Init FMS submodules:init_submodules"
        "Backend artifacts (sim/bridge/Autoware):backend_bootstrap"
        "Mirror backend assets to frontend/public:backend_seed_frontend_assets"
    )
    msg "═══ FMS Setup (backend: ${BACKEND_NAME}) ═══"
    run_steps "${STEPS[@]}"
    msg ""
    msg "═══ Setup complete ═══"
    msg "  Next: just up"

# Bring the full FMS dev stack up (sim + bridge + Autoware + API + frontend).
up:
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
    start_manual_control() {
        local mc_dir="${PROJECT_ROOT}/external/autoware_manual_control"
        if [ ! -d "$mc_dir" ]; then
            msg "  manual_control submodule not present; skipping (FMS UI will load but keyboard intent has no listener)"
            return 0
        fi
        # Prefer the FMS-owned config (Town01 presets, scope, modes) over the
        # submodule seed: $FMS_TELEOP_CONFIG -> fms_teleop_config.yaml -> seed.
        local cfg="${FMS_TELEOP_CONFIG:-${PROJECT_ROOT}/fms_teleop_config.yaml}"
        if [ ! -f "$cfg" ]; then
            cfg="${mc_dir}/teleop_config.yaml"
            local example="${cfg%.yaml}.example.yaml"
            if [ ! -f "$cfg" ] && [ -f "$example" ]; then
                msg "  Seeding teleop_config.yaml from .example (first run)"
                cp "$example" "$cfg"
            fi
        fi

        backend_exec_in_ros "cd '${mc_dir}' && \
            colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release \
                -DTELEOP_WITH_KEYBOARD=OFF -DTELEOP_WITH_ZENOH=ON" \
            || warn "manual_control build failed (backend container may not have source mounted)"

        msg "  Starting zenoh_control node..."
        backend_exec_in_ros -d "source '${mc_dir}/install/setup.bash' && \
            ros2 run autoware_manual_control zenoh_control --ros-args \
                --params-file '${cfg}' \
            > /tmp/zenoh_control.log 2>&1"
        sleep 5  # let the C++ node register subscribers before downstream services connect
    }
    start_fms_services() {
        backend_seed_frontend_assets

        if [ ! -x "${PROJECT_ROOT}/frontend/node_modules/.bin/react-scripts" ]; then
            msg "  react-scripts not installed — running npm install..."
            (cd "${PROJECT_ROOT}/frontend" && npm install 2>&1 | tail -5)
        fi

        # Backend-specific runtime flags (e.g. USE_BRIDGE_ROS2DDS for Carla);
        # REACT_APP_* are sourced from env.sh inside `just run`.
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

    STEPS=(
        "Cleanup previous instances:cleanup_previous"
        "Simulator (with per-deployment overrides):start_simulator"
        "Sim ↔ ROS bridge:backend_start_bridge"
        "Autoware ROS bringup:backend_start_autoware"
        "Manual control (build + launch):start_manual_control"
        "FMS API + Frontend (via just run):start_fms_services"
    )
    msg "═══ Starting FMS (backend: ${BACKEND_NAME}) ═══"
    backend_check_runtime_prereqs
    run_steps "${STEPS[@]}"
    msg ""
    msg "═══ Ready ═══"
    msg "  Frontend:  http://localhost:3000"
    msg "  API:       http://localhost:8000"
    msg "  Backend:   ${BACKEND_NAME}"
    msg ""
    msg "  Architecture: Frontend ⇄ ws ⇄ api_server ⇄ zenoh ⇄ zenoh_control ⇄ ROS ⇄ Autoware ⇄ ${BACKEND_NAME}"
    msg ""
    msg "  Run just down to stop."

# Tear the full FMS dev stack down (FMS services + backend + port orphans).
down:
    #!/usr/bin/env bash
    export FMS_ROOT='{{justfile_directory()}}'
    {{_lib}}
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

    # Backend (sim + bridge + autoware).
    backend_stop

    # Defensive: orphans on FMS-owned ports.
    for port in 3000 8000; do
        pids=$(lsof -ti :"$port" 2>/dev/null || true)
        if [ -n "$pids" ]; then
            kill $pids 2>/dev/null && msg "Killed orphans on :$port (pids: $pids)"
        fi
    done

    msg "═══ Stopped ═══"

# Remove Python build artifacts (does NOT stop a running stack — use `just down`).
clean:
    rm -rf __pycache__ .venv
