"""
BailBridge — Twilio SMS Helper

Provides a thin, typed wrapper around the Twilio REST client for sending
outbound SMS notifications related to bail cases.
"""

import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# Internal client (lazy singleton)
# ─────────────────────────────────────────────────────────────────────────────

_twilio_client: Client | None = None


def _get_client() -> Client:
    """Return a cached Twilio REST client, creating it on first call."""
    global _twilio_client
    if _twilio_client is None:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")

        if not account_sid or not auth_token:
            raise EnvironmentError(
                "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in your .env file."
            )

        _twilio_client = Client(account_sid, auth_token)
    return _twilio_client


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def send_sms(to: str, body: str) -> str:
    """
    Send a plain SMS message via Twilio.

    Args:
        to:   Recipient phone number in E.164 format (e.g. '+15551234567').
        body: Text content of the message (max 1600 chars).

    Returns:
        Twilio message SID on success.

    Raises:
        EnvironmentError: If Twilio credentials are missing.
        TwilioRestException: On Twilio API errors.
    """
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    if not from_number:
        raise EnvironmentError(
            "TWILIO_PHONE_NUMBER is not set. Add it to your .env file."
        )

    client = _get_client()
    message = client.messages.create(
        to=to,
        from_=from_number,
        body=body,
    )

    print(f"[SMS] ✅ Sent to {to} — SID: {message.sid}")
    return message.sid


# ── Convenience wrappers ──────────────────────────────────────────────────────

def notify_case_created(to: str, case_id: str, defendant_name: str) -> str:
    """Notify a defendant or agent that a new bail case has been opened."""
    body = (
        f"BailBridge: A new case has been opened for {defendant_name}. "
        f"Case ID: {case_id}. "
        "Log in to view details and next steps."
    )
    return send_sms(to, body)


def notify_evidence_uploaded(to: str, case_id: str, file_name: str) -> str:
    """Notify relevant parties that a new evidence file was uploaded."""
    body = (
        f"BailBridge: Evidence '{file_name}' has been uploaded to Case {case_id}. "
        "It is now available for review."
    )
    return send_sms(to, body)


def notify_bail_approved(to: str, case_id: str, amount: float) -> str:
    """Notify a defendant that their bail has been approved."""
    body = (
        f"BailBridge: Good news! Bail has been approved for Case {case_id}. "
        f"Amount: ${amount:,.2f}. Contact your bail agent for next steps."
    )
    return send_sms(to, body)
