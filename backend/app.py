import base64
import hashlib
import hmac
import json
import logging
import os
import tempfile

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

import audio_processor
import fulfillment
import lullaby_composer
import pdf_generator
import s3_handler

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pulse")

SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")
BASE_URL = os.getenv("BASE_URL", "https://pulseheirloom.com")
HAPTIC_PAGE = os.path.join(os.path.dirname(__file__), "web", "haptic", "index.html")

app = FastAPI(title="Pulse & Heirloom Studios API")


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@app.post("/webhook/shopify")
async def shopify_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive Shopify order-creation webhook.
    Returns 200 immediately (Shopify times out at 5s) and processes in background.
    """
    body = await request.body()

    # Verify HMAC-SHA256 signature
    if SHOPIFY_WEBHOOK_SECRET:
        hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")
        digest = hmac.new(SHOPIFY_WEBHOOK_SECRET.encode(), body, hashlib.sha256).digest()
        computed = base64.b64encode(digest).decode()
        if not hmac.compare_digest(computed, hmac_header):
            raise HTTPException(status_code=401, detail="Invalid Shopify HMAC signature")

    order = json.loads(body)
    order_id = str(order.get("id", "unknown"))
    log.info("Received Shopify webhook for order %s", order_id)

    background_tasks.add_task(run_pipeline, order_id, order)
    return {"status": "accepted", "order_id": order_id}


# ---------------------------------------------------------------------------
# Haptic experience page
# ---------------------------------------------------------------------------

@app.get("/listen/{order_id}")
async def haptic_page(order_id: str):
    if os.path.exists(HAPTIC_PAGE):
        return FileResponse(HAPTIC_PAGE, media_type="text/html")
    return JSONResponse(
        status_code=503,
        content={"error": "Haptic page not deployed — check web/haptic/index.html"},
    )


@app.get("/api/order/{order_id}")
async def order_data(order_id: str):
    meta_key = f"orders/{order_id}/metadata.json"
    if not s3_handler.key_exists(meta_key):
        raise HTTPException(status_code=404, detail="Order not found or still processing")

    metadata = s3_handler.download_json(meta_key)
    mp3_url = s3_handler.get_presigned_url(f"orders/{order_id}/lullaby.mp3", expiry=3600)

    return {
        "bpm": metadata.get("bpm"),
        "peaks": metadata.get("peaks", []),
        "mp3_url": mp3_url,
        "customer_name": metadata.get("customer_name", ""),
        "status": metadata.get("status", "complete"),
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def _extract_audio_url(order: dict) -> str:
    """
    Extract customer audio URL from Shopify order.
    Location depends on which file-upload app/method is used:
    - note_attributes (most common with upload apps like Uploadery)
    - line_item properties
    - order note
    """
    # Check note_attributes first
    for attr in order.get("note_attributes", []):
        if "audio" in attr.get("name", "").lower() or "file" in attr.get("name", "").lower():
            url = attr.get("value", "")
            if url.startswith("http"):
                return url

    # Check line item properties
    for item in order.get("line_items", []):
        for prop in item.get("properties", []):
            if "audio" in prop.get("name", "").lower() or "file" in prop.get("name", "").lower():
                url = prop.get("value", "")
                if url.startswith("http"):
                    return url

    # Check order note for a URL
    note = order.get("note", "") or ""
    for word in note.split():
        if word.startswith("http"):
            return word

    raise ValueError(
        "No audio URL found in order. "
        "Install a file-upload Shopify app (Uploadery, Customer Files) and ensure "
        "the upload field name contains 'audio' or 'file'."
    )


def _extract_customer_info(order: dict) -> dict:
    customer = order.get("customer", {})
    shipping = order.get("shipping_address", {})
    first = customer.get("first_name") or shipping.get("first_name", "")
    last = customer.get("last_name") or shipping.get("last_name", "")
    name = f"{first} {last}".strip() or "Valued Customer"

    # Baby name / due date from note_attributes
    baby_name = ""
    due_date = ""
    for attr in order.get("note_attributes", []):
        key = attr.get("name", "").lower()
        if "baby" in key or "name" in key:
            baby_name = attr.get("value", "")
        if "due" in key or "date" in key:
            due_date = attr.get("value", "")

    return {
        "name": name,
        "baby_name": baby_name,
        "due_date": due_date,
        "first_name": first,
        "last_name": last,
        "email": customer.get("email", order.get("email", "")),
        "phone": customer.get("phone", ""),
    }


def run_pipeline(order_id: str, order: dict) -> None:
    """Full order fulfillment pipeline (runs in background)."""
    log.info("[%s] Pipeline started", order_id)

    try:
        # 1. Get audio URL from order
        audio_url = _extract_audio_url(order)
        log.info("[%s] Audio URL: %s", order_id, audio_url[:80])

        # 2. Upload raw audio to S3
        raw_key = s3_handler.infer_s3_key(order_id, audio_url)
        s3_handler.upload_from_url(audio_url, raw_key)
        log.info("[%s] Raw audio uploaded to S3: %s", order_id, raw_key)

        # 3. Download for local processing
        tmp_dir = tempfile.gettempdir()
        local_input = os.path.join(tmp_dir, f"{order_id}_input{os.path.splitext(raw_key)[1]}")
        s3_handler.download_file(raw_key, local_input)

        # 4. Audio processing (FFmpeg + librosa)
        result = audio_processor.process_audio(local_input, order_id)
        bpm = result["bpm"]
        peaks = result["peaks"]
        cleaned_wav = result["cleaned_wav_path"]
        log.info("[%s] BPM detected: %.1f", order_id, bpm)

        # 5. Upload cleaned audio
        s3_handler.upload_file(cleaned_wav, f"orders/{order_id}/cleaned_audio.wav")

        # 6. Compose lullaby
        lullaby_path = os.path.join(tmp_dir, f"{order_id}_lullaby.mp3")
        lullaby_composer.compose(cleaned_wav, bpm, lullaby_path)
        s3_handler.upload_file(lullaby_path, f"orders/{order_id}/lullaby.mp3")
        log.info("[%s] Lullaby composed and uploaded", order_id)

        # 7. Generate print PDF
        customer_info = _extract_customer_info(order)
        pdf_path = os.path.join(tmp_dir, f"{order_id}_print.pdf")
        pdf_generator.generate(order_id, peaks, bpm, customer_info, pdf_path, BASE_URL)
        s3_handler.upload_file(pdf_path, f"orders/{order_id}/print.pdf")
        log.info("[%s] PDF generated and uploaded", order_id)

        # 8. Save metadata for haptic page API
        metadata = {
            "bpm": bpm,
            "peaks": peaks,
            "customer_name": customer_info["name"],
            "baby_name": customer_info.get("baby_name", ""),
            "status": "complete",
        }
        s3_handler.upload_json(metadata, f"orders/{order_id}/metadata.json")

        # 9. Submit to Gelato (7-day presigned URL so Gelato can retry safely)
        pdf_url = s3_handler.get_presigned_url(f"orders/{order_id}/print.pdf", expiry=86400 * 7)
        shipping = order.get("shipping_address", {})
        gelato_order_id = fulfillment.submit_print_order(order_id, pdf_url, shipping, customer_info)
        log.info("[%s] Gelato order submitted: %s", order_id, gelato_order_id)

        # 10. Update metadata with Gelato reference
        metadata["gelato_order_id"] = gelato_order_id
        s3_handler.upload_json(metadata, f"orders/{order_id}/metadata.json")

        log.info("[%s] Pipeline complete", order_id)

    except Exception as exc:
        log.error("[%s] Pipeline failed: %s", order_id, exc, exc_info=True)
        # Write failure status so the API endpoint can surface it
        try:
            s3_handler.upload_json(
                {"status": "failed", "error": str(exc)},
                f"orders/{order_id}/metadata.json",
            )
        except Exception:
            pass
