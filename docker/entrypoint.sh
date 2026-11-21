#!/bin/sh
set -e

# Default PORT for Cloud Run
export PORT="${PORT:-8080}"

# Substitute PORT into nginx configuration
rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf
envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

# Internal inter-service routing
export MEMBER1_AI_URL="${MEMBER1_AI_URL:-http://127.0.0.1:8001}"
export MEMBER3_VERIFY_URL="${MEMBER3_VERIFY_URL:-http://127.0.0.1:8002}"
export MEMBER2_API_URL="${MEMBER2_API_URL:-http://127.0.0.1:8000}"

# Ensure storage directory exists
mkdir -p /data/storage

# Run database migrations if DATABASE_URL is set
if [ -n "$DATABASE_URL" ]; then
    echo "Running Alembic migrations..."
    (cd /app/Member-2/backend && alembic upgrade head) || echo "Migration warning: proceeding with startup"
fi

# Start Member 1 AI service (port 8001)
echo "Starting Member 1 AI service on port 8001..."
cd /app/Member-1 && uvicorn app.main:app --host 127.0.0.1 --port 8001 &

# Start Member 3 verification service (port 8002)
echo "Starting Member 3 verification service on port 8002..."
cd /app/Member-3 && uvicorn app.main:app --host 127.0.0.1 --port 8002 &

# Start Member 2 core backend (port 8000)
echo "Starting Member 2 core backend on port 8000..."
cd /app/Member-2/backend && uvicorn app.main:app --host 127.0.0.1 --port 8000 &

# Start Nginx in foreground
echo "Starting Nginx reverse proxy on port $PORT..."
exec nginx -g "daemon off;"
