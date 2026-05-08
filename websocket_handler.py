"""
BailBridge — Socket.IO Event Handler  (Developer 1 · Phase 1)

Registers all real-time Socket.IO events on a shared AsyncServer instance.
Mount the companion ASGI app (`socket_app`) into FastAPI via main.py.

Events implemented (Phase 1 skeleton):
  connect          — authenticates the session and joins a case room.
  disconnect       — cleans up room membership.
  join_case        — client explicitly joins a case-specific room.
  leave_case       — client leaves a case-specific room.
  agent_update     — broadcast a status update to all clients in a case room.
  defendant_message — relay an inbound defendant message to the case room.
"""

import socketio

# ── Server setup ──────────────────────────────────────────────────────────────

# AsyncServer with ASGI transport.
# cors_allowed_origins mirrors the FastAPI CORS middleware setting.
# For Phase 1 development '*' is acceptable; restrict in production.
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=False,
)

# ASGI application to be mounted on the FastAPI app in main.py
socket_app = socketio.ASGIApp(sio, socketio_path="/ws/socket.io")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _case_room(case_id: str) -> str:
    """Canonical Socket.IO room name for a given case."""
    return f"case:{case_id}"


# ── Event handlers ────────────────────────────────────────────────────────────

@sio.event
async def connect(sid: str, environ: dict, auth: dict | None = None):
    """
    Fired when a client opens a Socket.IO connection.

    Phase 1: Log the connection and optionally extract an auth token for
    future JWT validation.  No hard authentication yet — that is Phase 2.
    """
    token = (auth or {}).get("token", "<no-token>")
    print(f"[WS] ✅ Client connected  sid={sid}  token={token!r}")
    # TODO (Phase 2): validate JWT and attach user context to session
    await sio.emit("connected", {"status": "ok", "sid": sid}, to=sid)


@sio.event
async def disconnect(sid: str):
    """Fired when a client disconnects (gracefully or otherwise)."""
    print(f"[WS] ❌ Client disconnected  sid={sid}")


@sio.event
async def join_case(sid: str, data: dict):
    """
    Client joins a case room to receive real-time updates for that case.

    Expected payload:
        { "case_id": "<firestore-case-id>" }
    """
    case_id = data.get("case_id")
    if not case_id:
        await sio.emit("error", {"message": "join_case requires a case_id"}, to=sid)
        return

    room = _case_room(case_id)
    sio.enter_room(sid, room)
    print(f"[WS] 📁 sid={sid} joined room={room}")
    await sio.emit("joined_case", {"case_id": case_id, "room": room}, to=sid)


@sio.event
async def leave_case(sid: str, data: dict):
    """
    Client leaves a case room.

    Expected payload:
        { "case_id": "<firestore-case-id>" }
    """
    case_id = data.get("case_id")
    if not case_id:
        await sio.emit("error", {"message": "leave_case requires a case_id"}, to=sid)
        return

    room = _case_room(case_id)
    sio.leave_room(sid, room)
    print(f"[WS] 🚪 sid={sid} left room={room}")
    await sio.emit("left_case", {"case_id": case_id}, to=sid)


@sio.event
async def agent_update(sid: str, data: dict):
    """
    Bail agent broadcasts a status update to everyone in a case room.

    Expected payload:
        {
            "case_id":  "<firestore-case-id>",
            "status":   "bail_approved" | "court_date_set" | "documents_ready" | ...,
            "message":  "Human-readable description",
        }
    """
    case_id = data.get("case_id")
    if not case_id:
        await sio.emit("error", {"message": "agent_update requires a case_id"}, to=sid)
        return

    room = _case_room(case_id)
    payload = {
        "case_id": case_id,
        "status":  data.get("status", "update"),
        "message": data.get("message", ""),
        "from_sid": sid,
    }
    print(f"[WS] 📢 agent_update → room={room}  status={payload['status']}")
    # Broadcast to ALL clients in the room (including sender)
    await sio.emit("case_update", payload, room=room)


@sio.event
async def defendant_message(sid: str, data: dict):
    """
    Relay an inbound defendant message to the case room.

    This is the Socket.IO counterpart to the Twilio webhook — for clients
    connected via the web app rather than SMS.

    Expected payload:
        {
            "case_id": "<firestore-case-id>",
            "text":    "Message text from the defendant",
        }
    """
    case_id = data.get("case_id")
    text = data.get("text", "").strip()

    if not case_id or not text:
        await sio.emit(
            "error",
            {"message": "defendant_message requires case_id and text"},
            to=sid,
        )
        return

    room = _case_room(case_id)
    payload = {
        "case_id":   case_id,
        "text":      text,
        "from_sid":  sid,
    }
    print(f"[WS] 💬 defendant_message → room={room}  text={text!r}")
    # TODO (Phase 2): persist message to Firestore before broadcasting
    await sio.emit("new_message", payload, room=room)
