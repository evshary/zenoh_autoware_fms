#!/bin/bash
#
# prepare_env.sh — bring up the FMS stack against a chosen backend.
#
# All backend-specific logic lives in backends/${BACKEND}.sh. This script
# orchestrates FMS-owned pieces (manual_control + just-managed services)
# and calls into the backend at the right lifecycle points.
#
# Usage:   ./prepare_env.sh                  # default backend (carla)
#          BACKEND=awsim ./prepare_env.sh    # future
#
# See backends/README.md for the contract; backends/carla.md for setup.

set -e
source "$(dirname "$0")/orchestrator.sh"

mkdir -p "${PROJECT_ROOT}/logs"
[ -f "${PROJECT_ROOT}/.env" ] && { set -a; source "${PROJECT_ROOT}/.env"; set +a; }

# ── Step functions ──────────────────────────────────────────

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
    local cfg="${mc_dir}/teleop_config.yaml"
    local example="${cfg%.yaml}.example.yaml"
    if [ ! -f "$cfg" ] && [ -f "$example" ]; then
        msg "  Seeding teleop_config.yaml from .example (first run)"
        cp "$example" "$cfg"
    fi

    backend_exec_in_ros "cd '${mc_dir}' && \
        colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release" \
        || warn "manual_control build failed (backend container may not have source mounted)"

    msg "  Starting remote_control node..."
    backend_exec_in_ros -d "source '${mc_dir}/install/setup.bash' && \
        ros2 run autoware_manual_control remote_control --ros-args \
            --params-file '${cfg}' -p start_as_external:=true \
        > /tmp/remote_control.log 2>&1"
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
    # shutdown can `kill -- -PGID`. CHOKIDAR_USEPOLLING avoids inotify
    # ENOSPC; BROWSER=none keeps `npm start` SSH-friendly.
    BROWSER=none CHOKIDAR_USEPOLLING=true \
        nohup setsid just run > "${PROJECT_ROOT}/logs/run.log" 2>&1 &
    echo "$!" > "${PROJECT_ROOT}/logs/just.pid"

    wait_for "API on :8000"      60 'curl -sf http://localhost:8000/'
    wait_for "Frontend on :3000" 60 'curl -sf http://localhost:3000/'
}

# ── Flow ────────────────────────────────────────────────────

STEPS=(
    "Cleanup previous instances:cleanup_previous"
    "Simulator (with per-deployment overrides):start_simulator"
    "Sim ↔ ROS bridge:backend_start_bridge"
    "Autoware ROS bringup:backend_start_autoware"
    "Manual control (build + launch):start_manual_control"
    "FMS API + Frontend (via just run):start_fms_services"
)

msg "═══ FMS Environment Setup (backend: ${BACKEND_NAME}) ═══"
backend_check_runtime_prereqs
run_steps "${STEPS[@]}"

cat <<EOF

═══ Ready ═══
  Frontend:  http://localhost:3000
  API:       http://localhost:8000
  Backend:   ${BACKEND_NAME}

  Architecture: Frontend ⇄ ws ⇄ api_server ⇄ zenoh ⇄ remote_control ⇄ ROS ⇄ Autoware ⇄ ${BACKEND_NAME}

  Run ./shutdown_env.sh to stop.
EOF
