#!/bin/bash

if [ -z "$GMI_API_KEY" ]; then
  echo "Warning: GMI_API_KEY is not set. API calls will fail."
  echo "Run: export GMI_API_KEY=\"your-key-here\" before starting."
  echo ""
fi

trap 'kill 0' EXIT

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOGFILE="$ROOT/makanmap.log"

if [ -f "$ROOT/.env" ]; then
  set -a
  source "$ROOT/.env"
  set +a
fi

echo "Starting backend on http://localhost:8000 ..."
(cd "$ROOT/backend" && uvicorn main:app --port 8000) > "$LOGFILE" 2>&1 &

echo "Starting frontend on http://localhost:3000 ..."
(cd "$ROOT/frontend" && python3 -m http.server 3000) > /dev/null 2>&1 &

echo ""
echo "MakanMap is running! Open http://localhost:3000"
echo "Logs: $LOGFILE"
echo ""
echo "To view logs:  tail -f $LOGFILE"
echo "Press Ctrl+C to stop."

wait
