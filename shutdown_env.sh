#!/bin/bash
#
# shutdown_env.sh — tear down everything prepare_env.sh started.
#
# FMS-owned services (just / parallel / uvicorn / npm) live in their
# own process group thanks to `setsid` in prepare_env.sh; one
# `kill -- -PGID` brings the whole subtree down. Backend-owned pieces
# (sim, bridge, autoware) are stopped via backend_stop.

source "$(dirname "$0")/orchestrator.sh"

PIDFILE="${PROJECT_ROOT}/logs/just.pid"

msg "═══ Shutting down FMS (backend: ${BACKEND_NAME}) ═══"

# ── FMS service tree: kill the whole process group in one shot ──
if [ -f "$PIDFILE" ]; then
    pgid=$(cat "$PIDFILE")
    if kill -- -"$pgid" 2>/dev/null; then
        msg "Stopped FMS service tree (PG $pgid)"
    fi
    rm -f "$PIDFILE"
fi

# ── Backend (sim + bridge + autoware) ──
backend_stop

# ── Defensive: orphans on FMS-owned ports ──
for port in 3000 8000; do
    pids=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        kill $pids 2>/dev/null && msg "Killed orphans on :$port (pids: $pids)"
    fi
done

msg "═══ Stopped ═══"
