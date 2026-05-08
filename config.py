"""
BailBridge — Centralised Configuration

All runtime secrets and settings are sourced from environment variables.
Load a .env file (via python-dotenv) before importing this module, or
inject the variables directly in your deployment environment.

Usage:
    from config import settings
    print(settings.firebase_storage_bucket)
"""

import os
from dotenv import load_dotenv

load_dotenv()


class _Settings:
    """
    Thin wrapper around os.getenv so every caller gets a typed,
    documented attribute rather than bare os.getenv() calls scattered
    throughout the codebase.
    """

    # ── Firebase ──────────────────────────────────────────────────────────────
    @property
    def firebase_service_account(self) -> str:
        """
        Path to the Firebase service-account JSON key file *or* the raw JSON
        string itself (useful for cloud-injected secrets).
        Raises EnvironmentError if not set.
        """
        value = os.getenv("FIREBASE_SERVICE_ACCOUNT")
        if not value:
            raise EnvironmentError(
                "FIREBASE_SERVICE_ACCOUNT is not set. "
                "Provide either a file path or the raw JSON in your .env file."
            )
        return value

    @property
    def firebase_storage_bucket(self) -> str:
        """
        Firebase Cloud Storage bucket name, e.g. 'your-project.appspot.com'.
        Raises EnvironmentError if not set.
        """
        value = os.getenv("FIREBASE_STORAGE_BUCKET")
        if not value:
            raise EnvironmentError(
                "FIREBASE_STORAGE_BUCKET is not set. "
                "Add it to your .env file (e.g. 'your-project.appspot.com')."
            )
        return value

    # ── Google APIs ───────────────────────────────────────────────────────────
    @property
    def gemini_api_key(self) -> str:
        """Google Gemini API key from Google AI Studio."""
        value = os.getenv("GEMINI_API_KEY")
        if not value:
            raise EnvironmentError("GEMINI_API_KEY is not set.")
        return value

    @property
    def google_maps_api_key(self) -> str:
        """Google Maps Platform API key."""
        value = os.getenv("GOOGLE_MAPS_API_KEY")
        if not value:
            raise EnvironmentError("GOOGLE_MAPS_API_KEY is not set.")
        return value

    # ── Twilio ────────────────────────────────────────────────────────────────
    @property
    def twilio_account_sid(self) -> str:
        value = os.getenv("TWILIO_ACCOUNT_SID")
        if not value:
            raise EnvironmentError("TWILIO_ACCOUNT_SID is not set.")
        return value

    @property
    def twilio_auth_token(self) -> str:
        value = os.getenv("TWILIO_AUTH_TOKEN")
        if not value:
            raise EnvironmentError("TWILIO_AUTH_TOKEN is not set.")
        return value

    @property
    def twilio_phone_number(self) -> str:
        value = os.getenv("TWILIO_PHONE_NUMBER")
        if not value:
            raise EnvironmentError("TWILIO_PHONE_NUMBER is not set.")
        return value

    # ── App ───────────────────────────────────────────────────────────────────
    @property
    def port(self) -> int:
        return int(os.getenv("PORT", "8000"))

    @property
    def debug(self) -> bool:
        return os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")

    # ── CORS ──────────────────────────────────────────────────────────────────
    @property
    def allowed_origins(self) -> list[str]:
        """
        Comma-separated list of allowed CORS origins.
        Defaults to wildcard ('*') for Phase 1 development convenience.
        Override in production: ALLOWED_ORIGINS=https://app.bailbridge.in
        """
        raw = os.getenv("ALLOWED_ORIGINS", "*")
        return [o.strip() for o in raw.split(",")]


# Singleton instance — import and use this everywhere.
settings = _Settings()
