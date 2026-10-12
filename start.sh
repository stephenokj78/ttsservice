#!/data/data/com.termux/files/usr/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

PORT=8099
LOG_FILE="$DIR/server.log"
PID_FILE="$DIR/server.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "TTSService is already running (PID: $PID)"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

echo "========================================"
echo "Starting TTSService on Port $PORT..."
echo "========================================"

nohup python3 -m uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1 >> "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo $NEW_PID > "$PID_FILE"

sleep 2
if ps -p "$NEW_PID" > /dev/null 2>&1; then
    echo "TTSService started successfully (PID: $NEW_PID) on http://0.0.0.0:$PORT"
else
    echo "Failed to start TTSService. Check $LOG_FILE"
    exit 1
fi
