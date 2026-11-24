#!/usr/bin/env bash
set -e

PROJECT_ID="trusty-obelisk-515402-p3"
REGION="us-central1"
SERVICE_NAME="aapke-liye"

echo "=========================================================="
echo " 🚀 Deploying Aapke Liye (Standalone Real) to Cloud Run"
echo " Project: $PROJECT_ID | Service: $SERVICE_NAME"
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/3] Building frontend..."
cd "$SCRIPT_DIR/frontend"
npm install --no-audit --no-fund
npm run build

echo "[2/3] Submitting Cloud Build..."
cd "$SCRIPT_DIR"
gcloud builds submit . --config=cloudbuild.yaml --project="$PROJECT_ID"

echo "[3/3] Deployment complete!"
gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" --format="value(status.url)"
