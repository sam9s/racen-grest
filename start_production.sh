#!/bin/bash
# Production startup script with proper process ordering
# This ensures Flask backend is ready before Next.js starts serving traffic

echo "[Startup] Starting Flask backend..."
python webhook_server.py &
FLASK_PID=$!

echo "[Startup] Waiting for Flask backend to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "[Startup] Flask backend is ready!"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo "[Startup] Waiting for Flask... attempt $ATTEMPT/$MAX_ATTEMPTS"
    sleep 1
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "[Startup] WARNING: Flask backend did not respond within timeout, starting Next.js anyway"
fi

echo "[Startup] Starting Next.js frontend..."
npx next start -p 5000 -H 0.0.0.0 &
NEXT_PID=$!

echo "[Startup] Both services running (Flask PID: $FLASK_PID, Next.js PID: $NEXT_PID)"

# Wait for both processes - if either exits, the container will restart
wait
