#!/bin/bash
#
# bootstrap.sh — prepare a freshly-cloned workspace so prepare_env.sh can run.
#
# Backend-aware: each backend declares its first-run setup in
# backends/${BACKEND}.sh::backend_bootstrap. This script orchestrates the
# FMS-owned pieces (zenoh-fms-engine image, Python venv, frontend deps)
# and dispatches to the backend for the rest.
#
# Usage:   ./bootstrap.sh                   # default backend (carla)
#          BACKEND=awsim ./bootstrap.sh     # explicit
#
# Idempotent — completed steps are detected and skipped on re-run.
# First run is slow (30–60 min) and downloads several GB. See
# backends/README.md for the contract; backends/<name>.md for setup.

set -e
source "$(dirname "$0")/orchestrator.sh"

IMG_FMS_ENGINE="zenoh-fms-engine:latest"

# ── Step functions ──────────────────────────────────────────

check_host_tools() {
    for t in docker git uv node npm just; do
        have "$t" || die "$t not in PATH"
    done
    backend_check_bootstrap_prereqs
}

init_submodules() {
    git -C "$PROJECT_ROOT" submodule update --init --recursive
}

build_fms_image() {
    [ -f "${PROJECT_ROOT}/zenoh_app/Dockerfile.fms" ] \
        || die "zenoh_app/Dockerfile.fms missing — can't build $IMG_FMS_ENGINE"
    skip_if_present "$IMG_FMS_ENGINE" \
        "docker image inspect '$IMG_FMS_ENGINE'" \
        "docker build -f '${PROJECT_ROOT}/zenoh_app/Dockerfile.fms' \
            -t '$IMG_FMS_ENGINE' '${PROJECT_ROOT}'"
}

sync_python_venv() {
    skip_if_present "Python .venv (uv sync)" \
        "[ -d '${PROJECT_ROOT}/.venv' ]" \
        "cd '$PROJECT_ROOT' && uv sync"
}

install_npm_deps() {
    skip_if_present "frontend node_modules" \
        "[ -x '${PROJECT_ROOT}/frontend/node_modules/.bin/react-scripts' ]" \
        "cd '${PROJECT_ROOT}/frontend' && npm install"
}

# ── Flow ────────────────────────────────────────────────────

STEPS=(
    "Host tooling check:check_host_tools"
    "Init FMS submodules:init_submodules"
    "Build zenoh-fms-engine image:build_fms_image"
    "Backend artifacts (sim/bridge/Autoware):backend_bootstrap"
    "Mirror backend assets to frontend/public:backend_seed_frontend_assets"
    "Sync Python venv via uv:sync_python_venv"
    "Install frontend npm deps:install_npm_deps"
)

msg "═══ FMS Bootstrap (backend: ${BACKEND_NAME}) ═══"
run_steps "${STEPS[@]}"

cat <<EOF

═══ Bootstrap complete ═══
  Next: cd $PROJECT_ROOT && ./prepare_env.sh
EOF
