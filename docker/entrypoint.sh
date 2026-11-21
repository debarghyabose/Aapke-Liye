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

# Start Member 1 AI service (port 8001)
echo "Starting Member 1 AI service on port 8001..."
cd /app/Member-1
python3 -u -m uvicorn app.main:app --host 127.0.0.1 --port 8001 > /tmp/member1.log 2>&1 &
PID_M1=$!

# Start Member 3 verification service (port 8002)
echo "Starting Member 3 verification service on port 8002..."
cd /app/Member-3
python3 -u -m uvicorn app.main:app --host 127.0.0.1 --port 8002 > /tmp/member3.log 2>&1 &
PID_M3=$!

# Start Member 2 core backend (port 8000)
echo "Starting Member 2 core backend on port 8000..."
cd /app/Member-2/backend
python3 -u -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > /tmp/member2.log 2>&1 &
PID_M2=$!

cd /app

echo "Waiting for services to start..."
sleep 5

echo "--- Member 1 Log (PID: $PID_M1) ---"
cat /tmp/member1.log

echo "--- Member 3 Log (PID: $PID_M3) ---"
cat /tmp/member3.log

echo "--- Member 2 Log (PID: $PID_M2) ---"
cat /tmp/member2.log

# Stream service logs to container stdout
tail -n 0 -F /tmp/member1.log /tmp/member2.log /tmp/member3.log &

# Start Nginx in foreground
echo "Starting Nginx reverse proxy on port $PORT..."
nginx -g "daemon off;"
