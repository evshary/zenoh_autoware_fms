#!/usr/bin/env bash
#
# orchestrator.sh — common helpers for FMS orchestrator scripts.
#
# Sourced by bootstrap.sh / prepare_env.sh / shutdown_env.sh. Resolves
# PROJECT_ROOT, picks a backend, sources backends/${BACKEND}.sh, and
# exposes utility functions used across all three orchestrators.
#
# Not meant to be run directly — `source` it.
#
# Public surface:
#   msg / warn / die / have               — output + checks
#   wait_for "label" timeout cmd          — poll a command until success
#   run_steps "${STEPS[@]}"               — run "Label:fn" entries, auto numbered
#   skip_if_present label check cmd       — idempotent build pattern
#
# Variables set:
#   PROJECT_ROOT  — absolute path to repo root (caller's directory)
#   BACKEND       — env-overridable backend name, defaults to "carla"
#   BACKEND_NAME  — set by the sourced backend script

# ── Resolve PROJECT_ROOT relative to the orchestrator that sourced us ──
# BASH_SOURCE[0] = this file; BASH_SOURCE[1] = the caller orchestrator.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[1]}")"; pwd)"
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
