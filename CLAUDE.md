# Pulse & Heirloom Studios

Automated heirloom audio print business. Customer uploads a fetal doppler recording → Python pipeline extracts audio, detects BPM, generates a lullaby MP3 + print-ready PDF, hosts a mobile haptic experience page → Gelato prints and ships the framed art. Zero manual fulfillment.

## Architecture

Three runtime concerns:
- **FastAPI microservice** (`/backend/`) — audio processing, PDF generation, webhook handler
- **Static haptic page** (`/web/haptic/`) — QR-scannable mobile page with audio + vibration
- **n8n orchestration** (`/n8n/`) — Shopify webhook relay, error handling, customer emails

S3 is the data backbone. All inter-component communication goes through S3 keys under `orders/{order_id}/`.

## Local Development

```bash
cp infrastructure/.env.example .env
# Fill in credentials, then:
docker-compose -f infrastructure/docker-compose.yml up
```

API available at http://localhost:8000  
n8n UI at http://localhost:5678 (admin / changeme)

Import the n8n workflow via the n8n UI: Settings → Import Workflow → select `n8n/workflow.json`

## Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `S3_BUCKET_NAME` | All order files stored here |
| `SHOPIFY_WEBHOOK_SECRET` | HMAC verification for incoming webhooks |
| `GELATO_PRODUCT_UID` | Must be created manually in Gelato dashboard first |
| `BASE_URL` | Root URL for QR codes (e.g. https://pulseheirloom.com) |
| `REDIS_URL` | Celery broker — use `redis://redis:6379/0` in Docker |

## Running Tests

```bash
docker-compose -f infrastructure/docker-compose.yml run api pytest tests/ -v
# Or locally (needs venv):
pip install -r backend/requirements.txt
pytest tests/ -v
```

## Critical Gotchas

- `numpy<2.0.0` is a hard pin — librosa 0.10.x breaks at runtime with NumPy 2.x
- `libsndfile1` must be installed in the Docker runtime image (not just build stage) — soundfile links dynamically
- `GELATO_PRODUCT_UID` is not invented — get it from your Gelato merchant dashboard after creating the 12"×16" wall art product
- iOS Safari does NOT support `navigator.vibrate` — the visual CSS pulse is the primary experience for iPhone users
- Shopify webhooks timeout after 5 seconds — the API returns 200 immediately and processes in background
- Gelato S3 presigned URLs must have 7-day expiry minimum — Gelato downloads asynchronously
- `assets/lullaby_template.mp3` must be sourced separately (royalty-free) — see `assets/README.md`
- PDF fonts must be TTF-embedded — standard Helvetica/Times are not embedded by reportlab and print services reject them

## S3 Key Schema

```
orders/{order_id}/raw_input.{ext}      # original customer upload
orders/{order_id}/cleaned_audio.wav    # FFmpeg filtered output
orders/{order_id}/lullaby.mp3          # tempo-matched lullaby with heartbeat
orders/{order_id}/print.pdf            # 12"×16" 300 DPI CMYK print file
orders/{order_id}/metadata.json        # {bpm, peaks, customer_name, status}
```

## Deployment

```bash
chmod +x infrastructure/deploy.sh
./infrastructure/deploy.sh
```

Configure Shopify webhook in Shopify Admin → Settings → Notifications → Webhooks:
- Event: Order creation
- URL: `https://your-domain.com/webhook/shopify`
- Format: JSON
