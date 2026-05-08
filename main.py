"""
BailBridge - FastAPI Application Entry Point
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn
import os

load_dotenv()

app = FastAPI(
    title="BailBridge",
    description="A legal tech platform bridging defendants and bail bond agents.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {"status": "ok", "app": "BailBridge"}


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
