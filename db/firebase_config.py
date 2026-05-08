"""
BailBridge — Firebase Admin SDK Client
Initializes a singleton Firebase app instance on first import.
"""

import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

_app: firebase_admin.App | None = None
_db: firestore.Client | None = None


def _initialize_firebase() -> firebase_admin.App:
    """
    Initialize the Firebase Admin SDK.

    Supports two modes:
    1. Path mode  — FIREBASE_SERVICE_ACCOUNT points to a JSON key file.
    2. JSON mode  — FIREBASE_SERVICE_ACCOUNT contains the raw JSON string
                    (useful for environment-injected secrets on cloud platforms).
    """
    if firebase_admin._apps:
        return firebase_admin.get_app()

    sa_value = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if not sa_value:
        raise EnvironmentError(
            "FIREBASE_SERVICE_ACCOUNT is not set. "
            "Provide either a file path or the raw JSON in your .env file."
        )

    # Determine if value is a file path or raw JSON
    if sa_value.strip().startswith("{"):
        service_account_info = json.loads(sa_value)
        cred = credentials.Certificate(service_account_info)
    else:
        cred = credentials.Certificate(sa_value)

    app = firebase_admin.initialize_app(cred)
    return app


def get_db() -> firestore.Client:
    """
    Return a Firestore client, initializing Firebase if necessary.
    This acts as a dependency-injectable singleton.
    """
    global _app, _db
    if _db is None:
        _app = _initialize_firebase()
        _db = firestore.client()
    return _db


# Eager initialization (optional — comment out to use lazy init via get_db())
try:
    get_db()
    print("[Firebase] ✅ Connected to Firestore successfully.")
except Exception as e:
    print(f"[Firebase] ⚠️  Could not initialize Firebase: {e}")
