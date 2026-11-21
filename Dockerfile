# ==============================================================================
# Stage 1: Build Frontend (Member-4)
# ==============================================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY Member-4/frontend/package*.json ./
RUN npm install

# Copy Member-3 offline-client (referenced by frontend mesh imports)
COPY Member-3/offline-client /app/Member-3/offline-client

# Copy frontend source files
COPY Member-4/frontend/ ./

# Build arguments for frontend API configuration
ARG VITE_API_URL="https://aapke-liye-uc3xzf5zpa-uc.a.run.app"
ARG VITE_MESH_URL="https://aapke-liye-uc3xzf5zpa-uc.a.run.app"
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_MESH_URL=$VITE_MESH_URL

RUN npm run build

# ==============================================================================
# Stage 2: Runtime Environment (FastAPI services + Nginx reverse proxy)
# ==============================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080 \
    APP_ENV=development \
    STORAGE_DIR=/data/storage

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    gettext-base \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specifications and install Python packages
COPY Member-1/requirements.txt ./Member-1/requirements.txt
COPY Member-2/backend/requirements.txt ./Member-2/backend/requirements.txt
COPY Member-3/requirements.txt ./Member-3/requirements.txt

RUN pip install --no-cache-dir -r ./Member-1/requirements.txt && \
    pip install --no-cache-dir -r ./Member-2/backend/requirements.txt && \
    pip install --no-cache-dir -r ./Member-3/requirements.txt

# Create storage directory with permissions
RUN mkdir -p /data/storage && chmod 777 /data/storage

# Copy frontend distribution files from Stage 1
COPY --from=frontend-builder /app/frontend/dist /var/www/html

# Copy application source code for services
COPY Member-1 /app/Member-1
COPY Member-2 /app/Member-2
COPY Member-3 /app/Member-3
COPY Member-5 /app/Member-5
COPY scripts /app/scripts

# Copy Nginx template and container entrypoint script
COPY docker/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8080

CMD ["/app/entrypoint.sh"]
