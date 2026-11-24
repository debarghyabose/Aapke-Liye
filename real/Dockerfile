# ==============================================================================
# Stage 1: Build Frontend
# ==============================================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./
ENV VITE_API_URL=""
ENV VITE_MESH_URL=""
ENV VITE_DEMO_MODE="false"

RUN npm run build

# ==============================================================================
# Stage 2: Runtime Environment
# ==============================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    STORAGE_DIR=/app/backend/storage \
    GOOGLE_CLOUD_PROJECT=trusty-obelisk-515402-p3

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install backend dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend application and data
COPY backend/ ./backend/

# Copy built frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Ensure storage directory exists
RUN mkdir -p /app/backend/storage && chmod 777 /app/backend/storage

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8080"]
