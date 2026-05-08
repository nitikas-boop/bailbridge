"""
BailBridge — Firebase Storage Handler

Provides upload_evidence() to:
  1. Upload file bytes to Firebase Cloud Storage under evidence/<case_id>/
  2. Generate a signed URL valid for 7 days.
  3. Write file metadata to Firestore under cases/<case_id>/evidence/<doc>.
"""

import datetime
import os
from typing import Optional

import firebase_admin
from firebase_admin import storage, firestore

from db.firebase_config import get_db


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_bucket():
    """
    Return the default Firebase Storage bucket.

    The bucket name must be set as FIREBASE_STORAGE_BUCKET in your .env
    (e.g. 'your-project-id.appspot.com').  If the Firebase app was already
    initialised by firebase_config.py we simply fetch it; otherwise we let
    firebase_admin raise a clear error.
    """
    bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")
    if not bucket_name:
        raise EnvironmentError(
            "FIREBASE_STORAGE_BUCKET is not set. "
            "Add it to your .env file (e.g. 'your-project.appspot.com')."
        )
    return storage.bucket(bucket_name)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def upload_evidence(
    file_bytes: bytes,
    file_name: str,
    case_id: str,
    content_type: Optional[str] = "application/octet-stream",
) -> str:
    """
    Upload evidence to Firebase Cloud Storage and record its metadata in
    Firestore.

    Args:
        file_bytes:   Raw bytes of the file to upload.
        file_name:    Original filename (e.g. 'warrant.pdf').
        case_id:      Firestore case document ID that this evidence belongs to.
        content_type: MIME type of the file (default: 'application/octet-stream').

    Returns:
        A signed HTTPS URL for the uploaded file, valid for 7 days.

    Raises:
        EnvironmentError: If FIREBASE_STORAGE_BUCKET is not configured.
        google.cloud.exceptions.GoogleCloudError: On Storage/Firestore errors.
    """
    # ── 1. Upload to Cloud Storage ────────────────────────────────────────────
    bucket = _get_bucket()
    blob_path = f"evidence/{case_id}/{file_name}"
    blob = bucket.blob(blob_path)

    blob.upload_from_string(
        file_bytes,
        content_type=content_type,
    )

    # ── 2. Generate a signed URL (7-day expiry) ───────────────────────────────
    expiry = datetime.timedelta(days=7)
    signed_url: str = blob.generate_signed_url(
        expiration=expiry,
        method="GET",
        version="v4",          # V4 signing — required for service-account creds
    )

    # ── 3. Write metadata to Firestore ────────────────────────────────────────
    db = get_db()
    now = datetime.datetime.utcnow()

    evidence_ref = (
        db.collection("cases")
        .document(case_id)
        .collection("evidence")
        .document()           # auto-generated document ID
    )

    evidence_ref.set(
        {
            "file_name": file_name,
            "storage_path": blob_path,
            "signed_url": signed_url,
            "url_expires_at": now + expiry,
            "content_type": content_type,
            "uploaded_at": now,
            "case_id": case_id,
        }
    )

    print(
        f"[StorageHandler] ✅ Uploaded '{file_name}' for case '{case_id}'. "
        f"Firestore doc: {evidence_ref.id}"
    )

    return signed_url
