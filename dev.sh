#!/bin/bash
#
# dev.sh — one entrypoint for the FMS dev stack.
#
#   ./dev.sh bootstrap   # one-time first-run setup (slow; downloads several GB)
#   ./dev.sh up          # bring the stack up   (alias: prepare)
#   ./dev.sh down        # tear the stack down  (alias: shutdown)
#
# Backend-aware: all backend-specific logic lives in backends/${BACKEND}.sh
# (default carla; override with BACKEND=<name>). See backends/README.md for
# the contract; backends/<name>.md for setup. `bootstrap` is idempotent —
# completed steps are detected and skipped on re-run.

# ── Shared helpers + backend resolution (self-contained) ────────────
#
# Public surface:
#   msg / warn / die / have               — output + checks
#   wait_for "label" timeout cmd          — poll a command until success
#   run_steps "${STEPS[@]}"               — run "Label:fn" entries, auto numbered
#   skip_if_present label check cmd       — idempotent build pattern
#
# Variables set:
#   PROJECT_ROOT  — absolute path to repo root (this script's directory)
#   BACKEND       — env-overridable backend name, defaults to "carla"
#   BACKEND_NAME  — set by the sourced backend script

# ── Resolve PROJECT_ROOT relative to this script ──
# BASH_SOURCE[0] = this file; fall back to $0 if BASH_SOURCE is unset.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")"; pwd)"
BACKEND="${BACKEND:-carla}"
BACKEND_SCRIPT="${PROJECT_ROOT}/backends/${BACKEND}.sh"

# ── Output helpers (plain prefixes; survive piping / redirection) ──
msg()  { printf '%s\n' "$*"; }
warn() { printf 'WARN: %s\n'  "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

# ── Resolve and source the backend script ──
[ -f "$BACKEND_SCRIPT" ] || die "unknown BACKEND='$BACKEND'; available: $(
    ls "${PROJECT_ROOT}/backends/"*.sh 2>/dev/null \
        | xargs -n1 basename 2>/dev/null | sed 's/\.sh$//' | tr '\n' ' '
)"
# shellcheck source=/dev/null
source "$BACKEND_SCRIPT"

# ── wait_for: poll a command until it succeeds, with timeout ──
# Replaces ad-hoc `for i in $(seq 1 N); do ...; sleep 1; done` loops.
# The cmd runs through `eval`, so quote it as a single string.
#   wait_for "API on :8000" 60 'curl -sf http://localhost:8000/'
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

# ── run_steps: execute a list of "Label:fn" entries with numbered banners ──
# Lets the orchestrator declare flow as data instead of imperative echos.
# Total step count is derived from $#; adding/removing a step in the
# caller's STEPS array renumbers automatically.
#
#   STEPS=("Cleanup:cleanup" "Simulator:backend_start_sim" ...)
#   run_steps "${STEPS[@]}"
#
# We use variadic "$@" rather than `arr=("${!1}")` array indirection
# because the latter can word-split entries containing whitespace
# (e.g. "Manual control (build + launch):...") on some bash versions,
# producing wrong totals and off-by-one numbering.
run_steps() {
    # Bash uses dynamic scoping, so a step function that does
    # `for i in ...` can clobber a `local i` here. Internal vars are
    # all `_step_*` prefixed to avoid that whole class of bug. (Real
    # incident: backend_start_sim's `for i in $(seq 1 40)` Carla-port
    # poll bumped this counter, producing 1/6 2/6 5/6 6/6 7/6 8/6.)
    local _step_total=$# _step_idx=1 _step_label _step_fn _step_entry
    for _step_entry in "$@"; do
        _step_label="${_step_entry%%:*}"
        _step_fn="${_step_entry##*:}"
        printf '\n[%d/%d] %s\n' "$_step_idx" "$_step_total" "$_step_label"
        "$_step_fn" || die "step [$_step_idx/$_step_total] '$_step_label' failed"
        _step_idx=$((_step_idx + 1))
    done
}

# ── skip_if_present: idempotent build pattern ──
# Runs `cmd` only when `check` fails. Both run through `eval`.
#   skip_if_present "lanelet map" '[ -f /path/file ]' 'docker run ...'
skip_if_present() {
    local label="$1" check="$2" cmd="$3"
    if eval "$check" >/dev/null 2>&1; then
        msg "  $label: already present — skipping"
    else
        msg "  $label: building..."
        eval "$cmd"
    fi
}

IMG_FMS_ENGINE="zenoh-fms-engine:latest"

# ── bootstrap step functions ────────────────────────────────

run_prerequisite() {
    # Host packages + uv sync + node/npm + map (the pre-existing
    # prerequisite.sh). bootstrap composes it; it does not duplicate it.
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

build_fms_image() {
    [ -f "${PROJECT_ROOT}/zenoh_app/Dockerfile.fms" ] \
        || die "zenoh_app/Dockerfile.fms missing — can't build $IMG_FMS_ENGINE"
    skip_if_present "$IMG_FMS_ENGINE" \
        "docker image inspect '$IMG_FMS_ENGINE'" \
        "docker build -f '${PROJECT_ROOT}/zenoh_app/Dockerfile.fms' \
            -t '$IMG_FMS_ENGINE' '${PROJECT_ROOT}'"
}

# ── up step functions ───────────────────────────────────────

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
    # `dev.sh down` can `kill -- -PGID`. CHOKIDAR_USEPOLLING avoids inotify
    # ENOSPC; BROWSER=none keeps `npm start` SSH-friendly.
    BROWSER=none CHOKIDAR_USEPOLLING=true \
        nohup setsid just run > "${PROJECT_ROOT}/logs/run.log" 2>&1 &
    echo "$!" > "${PROJECT_ROOT}/logs/just.pid"

    wait_for "API on :8000"      60 'curl -sf http://localhost:8000/'
    wait_for "Frontend on :3000" 60 'curl -sf http://localhost:3000/'
}

# ── Subcommands ─────────────────────────────────────────────

cmd_bootstrap() {
    set -e
    STEPS=(
        "Host prerequisites (prerequisite.sh):run_prerequisite"
        "Host tooling check:check_host_tools"
        "Init FMS submodules:init_submodules"
        "Build zenoh-fms-engine image:build_fms_image"
        "Backend artifacts (sim/bridge/Autoware):backend_bootstrap"
        "Mirror backend assets to frontend/public:backend_seed_frontend_assets"
    )
    msg "═══ FMS Bootstrap (backend: ${BACKEND_NAME}) ═══"
    run_steps "${STEPS[@]}"
    cat <<EOF

═══ Bootstrap complete ═══
  Next: cd $PROJECT_ROOT && ./dev.sh up
EOF
}

cmd_up() {
    set -e
    mkdir -p "${PROJECT_ROOT}/logs"
    [ -f "${PROJECT_ROOT}/.env" ] && { set -a; source "${PROJECT_ROOT}/.env"; set +a; }
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

  Run ./dev.sh down to stop.
EOF
}

cmd_down() {
    local pidfile="${PROJECT_ROOT}/logs/just.pid" pgid pids port
    msg "═══ Shutting down FMS (backend: ${BACKEND_NAME}) ═══"

    # FMS service tree: kill the whole process group in one shot.
    if [ -f "$pidfile" ]; then
        pgid=$(cat "$pidfile")
        if kill -- -"$pgid" 2>/dev/null; then
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
}

# ── Dispatch ────────────────────────────────────────────────

case "${1:-}" in
    bootstrap)      cmd_bootstrap ;;
    up|prepare)     cmd_up ;;
    down|shutdown)  cmd_down ;;
    *) die "usage: $(basename "$0") {bootstrap|up|down}  (BACKEND=<name> overrides; default carla)" ;;
esac
