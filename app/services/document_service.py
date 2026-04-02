import hashlib
import os
import uuid
from dataclasses import dataclass
from datetime import datetime

from google.cloud import storage


MAX_PDF_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "binary/octet-stream",
    "application/octet-stream",
}


@dataclass
class UploadedDocumentMeta:
    document_id: str
    object_key: str
    original_name: str
    content_type: str
    size_bytes: int
    sha256: str


def _get_bucket_name() -> str:
    bucket = os.getenv("GCS_UPLOAD_BUCKET", "").strip()
    if not bucket:
        raise ValueError("GCS upload bucket yapılandırılmamış. GCS_UPLOAD_BUCKET env değişkenini tanımlayın.")
    return bucket


def validate_pdf_bytes(file_name: str, content_type: str, file_bytes: bytes) -> str:
    safe_name = (file_name or "").strip()
    if not safe_name:
        raise ValueError("Dosya adı boş olamaz.")

    if not safe_name.lower().endswith(".pdf"):
        raise ValueError("Yalnızca .pdf uzantılı dosya yükleyebilirsiniz.")

    if not file_bytes:
        raise ValueError("PDF dosyası boş olamaz.")

    if len(file_bytes) > MAX_PDF_SIZE_BYTES:
        raise ValueError("PDF dosyası en fazla 20 MB olabilir.")

    normalized_type = (content_type or "").strip().lower()
    if normalized_type and normalized_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Geçersiz içerik tipi. Lütfen geçerli bir PDF dosyası yükleyin.")

    if not file_bytes.startswith(b"%PDF"):
        raise ValueError("Yüklenen dosya geçerli bir PDF imzası taşımıyor.")

    return hashlib.sha256(file_bytes).hexdigest()


def upload_pdf_to_gcs(file_name: str, content_type: str, file_bytes: bytes, sha256: str) -> UploadedDocumentMeta:
    bucket_name = _get_bucket_name()

    document_id = str(uuid.uuid4())
    now = datetime.utcnow()
    object_key = f"uploads/{now:%Y/%m/%d}/{document_id}.pdf"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_key)

    blob.metadata = {
        "original_name": file_name,
        "sha256": sha256,
    }
    blob.upload_from_string(file_bytes, content_type="application/pdf")

    return UploadedDocumentMeta(
        document_id=document_id,
        object_key=object_key,
        original_name=file_name,
        content_type=content_type or "application/pdf",
        size_bytes=len(file_bytes),
        sha256=sha256,
    )


def delete_pdf_from_gcs(object_key: str, bucket_name: str | None = None):
    target_bucket = (bucket_name or _get_bucket_name()).strip()
    storage_client = storage.Client()
    blob = storage_client.bucket(target_bucket).blob(object_key)
    blob.delete()
