"""
BailBridge — FastAPI Application Entry Point  (Developer 1 · Phase 1)

Start-up order:
  1. load_dotenv() picks up .env before anything else.
  2. config.settings exposes typed env-var accessors.
  3. CORSMiddleware is configured from settings.allowed_origins.
  4. websocket_handler.socket_app is mounted at /ws for real-time events.
  5. The Twilio webhook is registered for inbound SMS / Voice callbacks.
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn
import os

load_dotenv()  # Must run before importing config or any module that reads os.getenv

from config import settings                            # centralised env-var accessor
from websocket_handler import socket_app               # Socket.IO ASGI sub-application

app = FastAPI(
    title="BailBridge",
    description="A legal tech platform bridging defendants and bail bond agents.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # reads ALLOWED_ORIGINS env-var; defaults to ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Socket.IO (real-time events) ──────────────────────────────────────────────
# Mount the python-socketio ASGI app under /ws.
# Clients connect via:  wss://<host>/ws/socket.io/?EIO=4&transport=websocket
app.mount("/ws", socket_app)


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": "BailBridge",
        "version": app.version,
        "socket_io": "/ws/socket.io",
    }


@app.post("/webhook/twilio", tags=["Twilio"])
async def twilio_webhook(request: Request):
    """
    Placeholder webhook for incoming Twilio SMS/Voice events.
    Twilio will POST to this endpoint with message details.
    """
    form_data = await request.form()
    payload = dict(form_data)

    # TODO: Parse Twilio payload and dispatch to the appropriate agent
    print(f"[Twilio Webhook] Received payload: {payload}")

    # Return a TwiML response (empty for now)
    twiml_response = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
    return Response(content=twiml_response, media_type="application/xml")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
