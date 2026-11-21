#!/bin/sh

# Default PORT for Cloud Run
export PORT="${PORT:-8080}"

# Substitute PORT into nginx configuration
rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf
envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

# Internal inter-service routing
export MEMBER1_AI_URL="${MEMBER1_AI_URL:-http://127.0.0.1:8001}"
export MEMBER3_VERIFY_URL="${MEMBER3_VERIFY_URL:-http://127.0.0.1:8002}"
export MEMBER2_API_URL="${MEMBER2_API_URL:-http://127.0.0.1:8000}"

# Ensure storage and data directories exist
mkdir -p /data/storage /data/db /data/member3

# Run database migrations if DATABASE_URL is set
if [ -n "$DATABASE_URL" ]; then
    echo "Running Alembic migrations..."
    cd /app/Member-2/backend
    PYTHONPATH=/app/Member-2/backend alembic upgrade head || echo "Migration warning: proceeding with startup"
    cd /app
fi

# 1. Start Member 2 core backend FIRST (port 8000)
echo "Starting Member 2 core backend on port 8000..."
cd /app/Member-2/backend
python3 -c "import sys; print('Testing Member-2 import...'); from app.main import app; print('Member-2 import OK!')"
python3 -u -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
PID_M2=$!

# 2. Start Member 1 AI service (port 8001)
echo "Starting Member 1 AI service on port 8001..."
cd /app/Member-1
python3 -u -m uvicorn app.main:app --host 127.0.0.1 --port 8001 &
PID_M1=$!

# 3. Start Member 3 verification service (port 8002)
echo "Starting Member 3 verification service on port 8002..."
cd /app/Member-3
python3 -u -m uvicorn app.main:app --host 127.0.0.1 --port 8002 &
PID_M3=$!

cd /app

# Wait up to 15 seconds for Member 2 to respond
echo "Waiting for Member 2 core backend to be healthy..."
count=0
while [ $count -lt 15 ]; do
    status=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health || echo "000")
    if [ "$status" = "200" ]; then
        echo "Member 2 core backend is healthy (HTTP 200) after ${count}s!"
        break
    fi
    echo "Waiting for Member 2... (status: $status, elapsed: ${count}s)"
    sleep 1
    count=$((count + 1))
done

# Start Nginx in foreground
echo "Starting Nginx reverse proxy on port $PORT..."
nginx -g "daemon off;"
