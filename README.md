# Pulse & Heirloom Studios

> Automated heirloom audio print business — 100% hands-free fulfillment from customer upload to framed art at the door.

## What It Does

1. Customer orders on Shopify and uploads a fetal doppler audio/video clip
2. A Shopify webhook fires to this API
3. The Python pipeline:
   - Extracts and cleans the heartbeat audio (FFmpeg)
   - Detects exact BPM (librosa)
   - Generates a custom lullaby MP3 matching the baby's heart rate (pydub)
   - Renders a print-ready 300 DPI CMYK PDF with waveform art and QR code (reportlab)
   - Uploads all files to S3
   - Submits a print order to Gelato
4. Customer scans the QR code on their framed print → mobile haptic experience page plays the lullaby and pulses in sync with the detected BPM

## Prerequisites

- Docker + Docker Compose
- AWS S3 bucket (or use localstack for dev)
- Shopify store with a file upload app installed (Uploadery, Customer Files, or similar)
- Gelato merchant account with a 12"×16" wall art product configured
- `assets/lullaby_template.mp3` — a royalty-free piano track (see `assets/README.md`)
- `assets/fonts/Lato-Regular.ttf` and `assets/fonts/Lato-Light.ttf` (free from Google Fonts)

## Setup

### 1. Clone and configure environment

```bash
git clone https://github.com/jkmdale/Pulse-Studios-
cd Pulse-Studios-
cp infrastructure/.env.example .env
# Edit .env and fill in all credentials
```

### 2. Add required assets

```bash
# Download Lato font from Google Fonts, place in:
mkdir -p assets/fonts
# assets/fonts/Lato-Regular.ttf
# assets/fonts/Lato-Light.ttf

# Source a royalty-free piano track and place at:
# assets/lullaby_template.mp3
# See assets/README.md for specifications
```

### 3. Start services

```bash
docker-compose -f infrastructure/docker-compose.yml up -d
```

- API: http://localhost:8000
- n8n: http://localhost:5678 (admin / changeme)
- Redis: localhost:6379

### 4. Import n8n workflow

1. Open http://localhost:5678
2. Settings → Import Workflow
3. Select `n8n/workflow.json`
4. Set the `PYTHON_API_URL` environment variable in n8n to `http://api:8000`

### 5. Configure Shopify webhook

In Shopify Admin → Settings → Notifications → Webhooks:
- Event: **Order creation**
- URL: `https://your-domain.com/webhook/shopify`
- Format: JSON

Copy the webhook signing secret into your `.env` as `SHOPIFY_WEBHOOK_SECRET`.

### 6. Configure Gelato product UID

1. Log in to your Gelato merchant account
2. Create a product: 12"×16" poster (matte archival paper), framed or unframed as required
3. Copy the Product UID and set `GELATO_PRODUCT_UID` in your `.env`

## Deployment

```bash
chmod +x infrastructure/deploy.sh
./infrastructure/deploy.sh
```

Supports Railway (if `railway` CLI is installed) or Render (set `RENDER_API_KEY` + `RENDER_SERVICE_ID`).

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/webhook/shopify` | Shopify order webhook receiver |
| GET | `/listen/{order_id}` | Mobile haptic experience page |
| GET | `/api/order/{order_id}` | Order data (BPM, MP3 URL, peaks) |
| GET | `/health` | Health check |

## Testing

```bash
docker-compose -f infrastructure/docker-compose.yml run api pytest tests/ -v --tb=short
```

## File Structure

```
Pulse-Studios-/
├── backend/           Python microservice (FastAPI + processing pipeline)
├── web/haptic/        Mobile haptic experience page (HTML/JS, no dependencies)
├── n8n/               n8n workflow definition (import via UI)
├── infrastructure/    Dockerfile, docker-compose, deploy scripts
├── assets/            Fonts, lullaby template (must be sourced separately)
└── tests/             Pytest unit + integration tests
```

## Product Tiers

| Tier | Price | COGS | Margin |
|------|-------|------|--------|
| Digital Heirloom (MP3 + Haptic URL) | $29 | $0.05 | 99.8% |
| Essential Print (12"×16" unframed) | $59 | $8.50 | 85.6% |
| Signature Frame (framed + digital bundle) | $139 | $34.00 | 75.5% |
