import os
import uuid

import boto3
import httpx

_s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("S3_ENDPOINT_URL"),
    aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
    region_name=os.getenv("S3_REGION", "auto"),
)

BUCKET = os.getenv("S3_BUCKET", "merchant-screenshots")


async def save_screenshot(student_id: int, discord_url: str, content_type: str) -> str:
    """
    Скачивает файл с временной ссылки Discord и загружает в S3/MinIO.
    Возвращает s3_key — по нему потом можно сгенерировать ссылку обратно.
    """
    async with httpx.AsyncClient() as http:
        resp = await http.get(discord_url)
        resp.raise_for_status()
        file_bytes = resp.content

    ext = content_type.split("/")[-1] if content_type else "png"
    key = f"students/{student_id}/screenshots/{uuid.uuid4()}.{ext}"

    _s3.put_object(Bucket=BUCKET, Key=key, Body=file_bytes, ContentType=content_type)
    return key


def get_presigned_url(s3_key: str, expires_in: int = 900) -> str:
    """Временная ссылка на приватный файл — по умолчанию живёт 15 минут."""
    return _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": s3_key},
        ExpiresIn=expires_in,
    )


def ensure_bucket_exists():
    """Вызывается один раз при старте — создаёт bucket, если его ещё нет (актуально для MinIO)."""
    existing = [b["Name"] for b in _s3.list_buckets().get("Buckets", [])]
    if BUCKET not in existing:
        _s3.create_bucket(Bucket=BUCKET)