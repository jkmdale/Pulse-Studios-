#!/bin/bash
set -euo pipefail

echo "Deploying Pulse & Heirloom Studios API..."

# --- Railway ---
if command -v railway &>/dev/null; then
  echo "Deploying to Railway..."
  railway up --service pulse-api
  exit 0
fi

# --- Render (via API) ---
if [[ -n "${RENDER_API_KEY:-}" && -n "${RENDER_SERVICE_ID:-}" ]]; then
  echo "Triggering Render deploy..."
  curl -sf -X POST "https://api.render.com/v1/services/${RENDER_SERVICE_ID}/deploys" \
    -H "Authorization: Bearer ${RENDER_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{}'
  echo "Render deploy triggered."
  exit 0
fi

echo "Error: No deployment target configured."
echo "Set up Railway CLI or set RENDER_API_KEY + RENDER_SERVICE_ID env vars."
exit 1
