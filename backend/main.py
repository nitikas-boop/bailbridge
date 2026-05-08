"""
BailBridge — FastAPI Application Entry Point (Self-Sustaining Architecture)

Start-up order:
  1. load_dotenv() picks up .env.
  2. config.settings exposes env-var accessors.
  3. CORSMiddleware configured from settings.
  4. Socket.IO mounted at /ws.
  5. API endpoints for internal notifications and chat history.
"""

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bailbridge")

load_dotenv()

from config import settings
from websocket_handler import socket_app
from db import get_db
from agents import intake_agent, jatayu_agent

app = FastAPI(
    title="BailBridge",
    description="A self-sustaining legal tech platform with internal communications.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Socket.IO (real-time events) ──────────────────────────────────────────────
app.mount("/ws", socket_app)


# ── Health & Utility ──────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "app": "BailBridge",
        "version": app.version,
        "socket_io": "/ws/socket.io",
    }


# ── Internal Notification Center ─────────────────────────────────────────────

@app.get("/api/notifications/{user_id}", tags=["Notifications"])
async def get_notifications(user_id: str):
    """Fetch the last 10 notifications for a specific user."""
    try:
        db = get_db()
        notifications_ref = db.collection("notifications")
        query = (
            notifications_ref.where("user_id", "==", user_id)
            .order_by("created_at", direction="DESCENDING")
            .limit(10)
        )
        docs = query.stream()
        
        results = []
        for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id
            # Convert datetime objects to string for JSON serialization
            if "created_at" in d:
                d["created_at"] = d["created_at"].isoformat()
            results.append(d)
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Chat History Bridge ──────────────────────────────────────────────────────

@app.get("/api/chat/history/{case_id}", tags=["Chat"])
async def get_chat_history(case_id: str):
    """Fetch all previous messages for a specific case thread."""
    try:
        db = get_db()
        conversations_ref = db.collection("conversations")
        query = (
            conversations_ref.where("case_id", "==", case_id)
            .order_by("timestamp", direction="ASCENDING")
        )
        docs = query.stream()
        
        messages = []
        for doc in docs:
            m = doc.to_dict()
            m["id"] = doc.id
            if "timestamp" in m:
                m["timestamp"] = m["timestamp"].isoformat()
            messages.append(m)
            
        return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Case Management ──────────────────────────────────────────────────────────

@app.post("/api/start-case", tags=["Cases"])
async def start_case():
    """
    Generate a new case, initialize in Firestore, and trigger the Intake Agent.
    """
    try:
        case_id = f"BB-{uuid.uuid4().hex[:8].upper()}"
        db = get_db()
        
        # 1. Initialize case document in Firestore
        case_ref = db.collection("cases").document(case_id)
        case_ref.set({
            "case_id": case_id,
            "status": "intake_started",
            "created_at": datetime.datetime.utcnow(),
            "last_updated": datetime.datetime.utcnow()
        })
        
        # 2. Trigger Intake Agent (async)
        # Note: We trigger this after the response or as a background task
        # so the API remains responsive.
        await intake_agent.start_interview(case_id)
        
        return {
            "status": "success",
            "case_id": case_id,
            "message": "Intake process initialized."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sahayak-script/{case_id}", tags=["Cases"])
async def get_sahayak_script(case_id: str):
    """
    Fetch or generate the 3-point Sahayak verbal script for a case.
    """
    try:
        from agents.jatayu import jatayu_agent
        script = await jatayu_agent.generate_sahayak_script(case_id)
        return {
            "case_id": case_id,
            "sahayak_script": script
        }
    except Exception as e:
        logger.error(f"[API] [Error] Failed to get Sahayak script: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True,
    )
