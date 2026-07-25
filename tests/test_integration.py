"""
End-to-end integration test.

Uses moto to mock S3 and responses to mock Gelato — no real AWS or Gelato calls.
Generates a synthetic heartbeat WAV and runs the full pipeline.
"""
import json
import os
import sys

import boto3
import moto
import numpy as np
import pytest
import responses as responses_lib
import soundfile as sf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

BUCKET = "pulse-heirloom-orders"
GELATO_URL = "https://order.gelatoapis.com/v4/orders"

SAMPLE_ORDER = {
    "id": 99001,
    "email": "test@example.com",
    "customer": {
        "first_name": "Test",
        "last_name": "Parent",
        "email": "test@example.com",
        "phone": "+64 21 000 1234",
    },
    "shipping_address": {
        "first_name": "Test",
        "last_name": "Parent",
        "address1": "1 Test St",
        "address2": "",
        "city": "Auckland",
        "zip": "1010",
        "country_code": "NZ",
    },
    "note_attributes": [],
    "line_items": [],
    "note": "",
}


@pytest.fixture
def mock_s3(monkeypatch, tmp_path):
    """Set up moto S3 mock and patch s3_handler to use it."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_REGION", "ap-southeast-2")
    monkeypatch.setenv("S3_BUCKET_NAME", BUCKET)
    monkeypatch.setenv("GELATO_API_KEY", "test-key")
    monkeypatch.setenv("GELATO_PRODUCT_UID", "poster-12x16")
    monkeypatch.setenv("BASE_URL", "https://pulseheirloom.com")
    return tmp_path


@pytest.fixture
def heartbeat_wav(tmp_path):
    """Generate a synthetic heartbeat WAV."""
    sr = 44100
    duration = 8.0
    bpm_freq = 145.0 / 60.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    signal = (np.sin(2 * np.pi * bpm_freq * t) * 0.5).astype(np.float32)
    path = str(tmp_path / "heartbeat.wav")
    sf.write(path, signal, sr)
    return path


@moto.mock_s3
@responses_lib.activate
def test_full_pipeline_wav_to_s3(mock_s3, heartbeat_wav, monkeypatch):
    """Run pipeline with a WAV file injected via order note_attributes."""
    import importlib
    import s3_handler
    import app as app_module

    # Create the S3 bucket
    boto3.client(
        "s3",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        region_name="ap-southeast-2",
    ).create_bucket(
        Bucket=BUCKET,
        CreateBucketConfiguration={"LocationConstraint": "ap-southeast-2"},
    )
    importlib.reload(s3_handler)

    # Serve the heartbeat WAV over HTTP so upload_from_url works
    with open(heartbeat_wav, "rb") as f:
        wav_bytes = f.read()

    responses_lib.add(
        responses_lib.GET,
        "https://cdn.shopify.com/orders/heartbeat.wav",
        body=wav_bytes,
        status=200,
        stream=True,
    )

    # Mock Gelato
    responses_lib.add(
        responses_lib.POST,
        GELATO_URL,
        json={"id": "gelato-test-999"},
        status=201,
    )

    order = dict(SAMPLE_ORDER)
    order["note_attributes"] = [
        {"name": "audio_file", "value": "https://cdn.shopify.com/orders/heartbeat.wav"}
    ]

    # Run the pipeline synchronously
    importlib.reload(app_module)
    app_module.run_pipeline("99001", order)

    # Verify all expected S3 objects exist
    s3 = boto3.client(
        "s3",
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        region_name="ap-southeast-2",
    )

    def key_exists(key):
        try:
            s3.head_object(Bucket=BUCKET, Key=key)
            return True
        except Exception:
            return False

    assert key_exists("orders/99001/raw_input.wav"), "Raw audio not uploaded"
    assert key_exists("orders/99001/cleaned_audio.wav"), "Cleaned audio not uploaded"
    assert key_exists("orders/99001/lullaby.mp3"), "Lullaby MP3 not uploaded"
    assert key_exists("orders/99001/print.pdf"), "Print PDF not uploaded"
    assert key_exists("orders/99001/metadata.json"), "Metadata not uploaded"

    # Verify metadata content
    meta_obj = s3.get_object(Bucket=BUCKET, Key="orders/99001/metadata.json")
    metadata = json.loads(meta_obj["Body"].read())
    assert metadata["status"] == "complete"
    assert 100 <= metadata["bpm"] <= 220
    assert isinstance(metadata["peaks"], list)
    assert len(metadata["peaks"]) > 0
    assert metadata["gelato_order_id"] == "gelato-test-999"
