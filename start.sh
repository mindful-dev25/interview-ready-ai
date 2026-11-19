#!/usr/bin/env bash
# Starts both halves in one container: FastAPI on 127.0.0.1:8000 (private) and Next.js on $PORT (public).
# If either one exits, the other is stopped too, so the container exits and the host restarts it.
set -uo pipefail

cd /app/backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
backend=$!

cd /app/frontend
HOSTNAME=0.0.0.0 PORT="${PORT:-10000}" node server.js &
frontend=$!

trap 'kill -TERM "$backend" "$frontend" 2>/dev/null' TERM INT
wait -n
status=$?
kill -TERM "$backend" "$frontend" 2>/dev/null
wait
exit "$status"
