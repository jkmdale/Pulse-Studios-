import json
import os
import tempfile
from typing import Optional

import boto3
import requests
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

_s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION", "ap-southeast-2"),
)
BUCKET = os.getenv("S3_BUCKET_NAME", "pulse-heirloom-orders")


def upload_file(local_path: str, s3_key: str) -> str:
    _s3.upload_file(local_path, BUCKET, s3_key)
    return s3_key


def download_file(s3_key: str, local_path: str) -> None:
    _s3.download_file(BUCKET, s3_key, local_path)


def upload_from_url(remote_url: str, s3_key: str) -> str:
    """Stream file from remote URL directly into S3 without buffering to disk."""
    with requests.get(remote_url, stream=True, timeout=60) as r:
        r.raise_for_status()
        _s3.upload_fileobj(r.raw, BUCKET, s3_key)
    return s3_key


def get_presigned_url(s3_key: str, expiry: int = 86400 * 7) -> str:
    """7-day expiry by default — Gelato downloads asynchronously and may retry."""
    return _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": s3_key},
        ExpiresIn=expiry,
    )


def upload_json(data: dict, s3_key: str) -> str:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    _s3.put_object(Bucket=BUCKET, Key=s3_key, Body=body, ContentType="application/json")
    return s3_key


def download_json(s3_key: str) -> dict:
    obj = _s3.get_object(Bucket=BUCKET, Key=s3_key)
    return json.loads(obj["Body"].read())


def key_exists(s3_key: str) -> bool:
    try:
        _s3.head_object(Bucket=BUCKET, Key=s3_key)
        return True
    except ClientError:
        return False


def upload_bytes(data: bytes, s3_key: str, content_type: str = "application/octet-stream") -> str:
    """Upload raw bytes to S3 (used by the /upload endpoint for browser-submitted files)."""
    _s3.put_object(Bucket=BUCKET, Key=s3_key, Body=data, ContentType=content_type)
    return s3_key


def infer_s3_key(order_id: str, remote_url: str) -> str:
    """Derive S3 key from remote URL extension."""
    ext = remote_url.rsplit(".", 1)[-1].lower().split("?")[0]
    supported = {"mov", "mp4", "m4a", "mp3", "wav", "3gp", "aac"}
    if ext not in supported:
        ext = "mov"
    return f"orders/{order_id}/raw_input.{ext}"
