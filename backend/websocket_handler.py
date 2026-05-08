"""
BailBridge — Socket.IO Event Handler (The Chat Engine)

Handles real-time communication and persists all messages to Firestore.
All messages are grouped by case_id to preserve chat history.
"""

import socketio
import datetime
from db import get_db

# ── Server setup ──────────────────────────────────────────────────────────────

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=False,
)

socket_app = socketio.ASGIApp(sio, socketio_path="/ws/socket.io")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _case_room(case_id: str) -> str:
    """Canonical Socket.IO room name for a given case."""
    return f"case:{case_id}"

async def _persist_message(case_id: str, sender_id: str, text: str, sender_type: str):
    """Save message to the 'conversations' collection in Firestore."""
    db = get_db()
    message_data = {
        "case_id": case_id,
        "sender_id": sender_id,
        "sender_type": sender_type,  # 'defendant', 'agent', or 'ai'
        "text": text,
        "timestamp": datetime.datetime.utcnow()
    }
    
    # Save to Firestore
    doc_ref = db.collection("conversations").document()
    doc_ref.set(message_data)
    return doc_ref.id


# ── Event handlers ────────────────────────────────────────────────────────────

@sio.event
async def connect(sid: str, environ: dict, auth: dict | None = None):
    """Fired when a client opens a Socket.IO connection."""
    token = (auth or {}).get("token", "<no-token>")
    print(f"[WS] [OK] Client connected sid={sid} token={token!r}")
    await sio.emit("connected", {"status": "ok", "sid": sid}, to=sid)


@sio.event
async def disconnect(sid: str):
    """Fired when a client disconnects."""
    print(f"[WS] [Disconnect] Client disconnected sid={sid}")


@sio.event
async def join_case(sid: str, data: dict):
    """Client joins a case room to receive real-time updates."""
    case_id = data.get("case_id")
    if not case_id:
        await sio.emit("error", {"message": "join_case requires a case_id"}, to=sid)
        return

    room = _case_room(case_id)
    sio.enter_room(sid, room)
    print(f"[WS] [Join] sid={sid} joined room={room}")
    await sio.emit("joined_case", {"case_id": case_id, "room": room}, to=sid)


@sio.event
async def leave_case(sid: str, data: dict):
    """Client leaves a case room."""
    case_id = data.get("case_id")
    if not case_id:
        await sio.emit("error", {"message": "leave_case requires a case_id"}, to=sid)
        return

    room = _case_room(case_id)
    sio.leave_room(sid, room)
    print(f"[WS] [Leave] sid={sid} left room={room}")
    await sio.emit("left_case", {"case_id": case_id}, to=sid)


@sio.event
async def agent_update(sid: str, data: dict):
    """
    Bail agent or AI broadcasts a status update/message.
    Now persists to Firestore before broadcasting.
    """
    case_id = data.get("case_id")
    text = data.get("message", "")
    sender_id = data.get("sender_id", sid)
    
    if not case_id or not text:
        await sio.emit("error", {"message": "agent_update requires case_id and message"}, to=sid)
        return

    # Persist to Firestore
    await _persist_message(case_id, sender_id, text, "agent")

    room = _case_room(case_id)
    payload = {
        "case_id": case_id,
        "status": data.get("status", "update"),
        "message": text,
        "from_sid": sid,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    print(f"[WS] [Broadcast] agent_update -> room={room}")
    await sio.emit("case_update", payload, room=room)


@sio.event
async def defendant_message(sid: str, data: dict):
    """
    Relay an inbound defendant message and persist it.
    """
    case_id = data.get("case_id")
    text = data.get("text", "").strip()
    sender_id = data.get("sender_id", sid)

    if not case_id or not text:
        await sio.emit("error", {"message": "defendant_message requires case_id and text"}, to=sid)
        return

    # Persist to Firestore
    await _persist_message(case_id, sender_id, text, "defendant")

    room = _case_room(case_id)
    payload = {
        "case_id": case_id,
        "text": text,
        "from_sid": sid,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    print(f"[WS] [Message] defendant_message -> room={room}")
    await sio.emit("new_message", payload, room=room)
    
    # --- Trigger Jatayu Classification & Routing ---
    import asyncio
    try:
        from agents import jatayu_agent
        asyncio.create_task(jatayu_agent.classify_and_route(case_id, text))
    except Exception as e:
        print(f"[WS] [Warning] Error triggering Jatayu: {e}")


@sio.event
async def file_uploaded(sid: str, data: dict):
    """
    Triggered when a user uploads a document to the vault.
    Refreshes the Bail PDF to include new evidence.
    """
    case_id = data.get("case_id")
    file_name = data.get("file_name", "document")
    
    if not case_id:
        return

    print(f"[WS] [Upload] File {file_name} uploaded for case {case_id}")
    
    # Notify User
    await sio.emit("case_update", {
        "case_id": case_id,
        "status": "refreshing_pdf",
        "message": f"I've updated your draft with the new evidence: {file_name}!"
    }, room=_case_room(case_id))

    # Trigger Architect to refresh PDF
    import asyncio
    try:
        from agents import bail_agent
        asyncio.create_task(bail_agent.analyze_strategy(case_id))
    except Exception as e:
        print(f"[WS] [Warning] Error refreshing PDF: {e}")

@sio.event
async def agent_typing(sid: str, data: dict):
    """
    Broadcast typing indicator (boolean).
    Payload: { "case_id": "...", "is_typing": true/false }
    """
    case_id = data.get("case_id")
    is_typing = data.get("is_typing", False)
    
    if not case_id:
        return

    room = _case_room(case_id)
    await sio.emit("agent_typing_status", {"is_typing": is_typing}, room=room, skip_sid=sid)
