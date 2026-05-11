import json
import logging
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_token
from app.core.time import ensure_aware_utc, utc_now
from app.models.dataset import Sheet as SheetModel, WebSocketTicket
from app.models.user import User
from app.services.websocket_manager import manager
from app.services.permissions import sheet_role

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_PRESENCE_MESSAGE_BYTES = 2048
MAX_CONNECTIONS_PER_USER_PER_SHEET = 3
PRESENCE_RATE_LIMIT = 30
PRESENCE_RATE_WINDOW_SECONDS = 10
MAX_PRESENCE_ROW = 1_000_000
MAX_PRESENCE_COLUMN_LENGTH = 128
PRESENCE_CLOSE_CODE = 1008

CURSOR_MESSAGE_TYPES = {"cursor", "cursor_move"}


class PresenceRateLimiter:
    """Small in-process sliding-window limiter for WebSocket fanout messages."""

    def __init__(self) -> None:
        self._hits: Dict[Tuple[int, int], Deque[float]] = defaultdict(deque)

    def reset(self) -> None:
        self._hits.clear()

    def allow(self, user_id: int, sheet_id: int) -> bool:
        now = time.monotonic()
        key = (user_id, sheet_id)
        hits = self._hits[key]

        while hits and now - hits[0] > PRESENCE_RATE_WINDOW_SECONDS:
            hits.popleft()

        if len(hits) >= PRESENCE_RATE_LIMIT:
            return False

        hits.append(now)
        return True


presence_rate_limiter = PresenceRateLimiter()


class WebSocketPayloadError(ValueError):
    def __init__(self, code: str, reason: str, *, close: bool = False) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.close = close


async def get_user_from_ticket(ticket: str, sheet_id: int, db: Session) -> User | None:
    """Consume a one-time WebSocket ticket and return its active user."""
    now = utc_now()
    ticket_record = (
        db.query(WebSocketTicket)
        .filter(
            WebSocketTicket.ticket_hash == hash_token(ticket),
            WebSocketTicket.sheet_id == sheet_id,
        )
        .first()
    )
    if (
        not ticket_record
        or ticket_record.consumed_at is not None
        or ensure_aware_utc(ticket_record.expires_at) <= now
    ):
        return None
    user = db.query(User).filter(User.id == ticket_record.user_id).first()
    sheet = db.query(SheetModel).filter(SheetModel.id == sheet_id).first()
    if not user or not user.is_active or not sheet or not sheet_role(db, sheet, user):
        return None

    ticket_record.consumed_at = now
    db.commit()
    return user


def _decode_message(data: str) -> dict:
    if len(data.encode("utf-8")) > MAX_PRESENCE_MESSAGE_BYTES:
        raise WebSocketPayloadError(
            "payload_too_large",
            "WebSocket message exceeds the maximum presence payload size.",
            close=True,
        )

    try:
        message = json.loads(data)
    except json.JSONDecodeError as exc:
        raise WebSocketPayloadError(
            "invalid_json",
            "WebSocket messages must be valid JSON objects.",
        ) from exc

    if not isinstance(message, dict):
        raise WebSocketPayloadError(
            "invalid_payload",
            "WebSocket messages must be JSON objects.",
        )

    message_type = message.get("type")
    if not isinstance(message_type, str) or not message_type:
        raise WebSocketPayloadError(
            "invalid_payload",
            "WebSocket messages must include a string type.",
        )

    return message


def _validate_row(value, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WebSocketPayloadError(
            "invalid_payload",
            f"{field} must be an integer row index.",
        )
    if value < 0 or value > MAX_PRESENCE_ROW:
        raise WebSocketPayloadError(
            "invalid_payload",
            f"{field} is outside the allowed row range.",
        )
    return value


def _validate_column(value, field: str):
    if isinstance(value, bool):
        raise WebSocketPayloadError(
            "invalid_payload",
            f"{field} must be a column name or index.",
        )
    if isinstance(value, int):
        if value < 0 or value > MAX_PRESENCE_ROW:
            raise WebSocketPayloadError(
                "invalid_payload",
                f"{field} is outside the allowed column range.",
            )
        return value
    if isinstance(value, str):
        if not value or len(value) > MAX_PRESENCE_COLUMN_LENGTH:
            raise WebSocketPayloadError(
                "invalid_payload",
                f"{field} is outside the allowed column size.",
            )
        return value
    raise WebSocketPayloadError(
        "invalid_payload",
        f"{field} must be a column name or index.",
    )


def _cursor_payload(message: dict, user: User) -> dict:
    message_type = message["type"]
    return {
        "type": message_type,
        "user_id": user.id,
        "username": user.username,
        "row": _validate_row(message.get("row"), "row"),
        "column": _validate_column(message.get("column"), "column"),
    }


def _selection_payload(message: dict, user: User) -> dict:
    return {
        "type": "selection",
        "user_id": user.id,
        "username": user.username,
        "start_row": _validate_row(message.get("start_row"), "start_row"),
        "start_column": _validate_column(message.get("start_column"), "start_column"),
        "end_row": _validate_row(message.get("end_row"), "end_row"),
        "end_column": _validate_column(message.get("end_column"), "end_column"),
    }


def _active_connection_count(sheet_id: int, user_id: int) -> int:
    return sum(
        1
        for info in manager.connection_info.values()
        if info["sheet_id"] == sheet_id and info["user_id"] == user_id
    )


async def _send_websocket_error(websocket: WebSocket, code: str, reason: str) -> None:
    await manager.send_personal_message(
        websocket,
        {
            "type": "error",
            "code": code,
            "reason": reason,
        },
    )


async def _disconnect_and_notify(websocket: WebSocket, sheet_id: int) -> None:
    info = manager.disconnect(websocket)
    if not info:
        return

    await manager.broadcast_to_sheet(
        sheet_id,
        {
            "type": "user_left",
            "user_id": info["user_id"],
            "username": info["username"],
            "active_users": len(manager.active_connections.get(sheet_id, [])),
        },
    )


@router.websocket("/collaborate/{sheet_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    sheet_id: int,
    ticket: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time collaboration."""
    # Authenticate user
    user = await get_user_from_ticket(ticket, sheet_id, db)
    if not user:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    # Verify sheet exists and user has access
    sheet = db.query(SheetModel).filter(SheetModel.id == sheet_id).first()
    
    if not sheet or not sheet_role(db, sheet, user):
        await websocket.close(code=1008, reason="Sheet not found")
        return

    if _active_connection_count(sheet_id, user.id) >= MAX_CONNECTIONS_PER_USER_PER_SHEET:
        await websocket.close(code=1008, reason="Too many active sheet connections")
        return
    
    # Connect user
    await manager.connect(websocket, sheet_id, user.id, user.username)
    
    try:
        # Send initial state
        await manager.send_personal_message(websocket, {
            "type": "connected",
            "sheet_id": sheet_id,
            "active_users": manager.get_active_users(sheet_id)
        })
        
        # Listen for messages
        while True:
            data = await websocket.receive_text()
            try:
                message = _decode_message(data)
            except WebSocketPayloadError as exc:
                await _send_websocket_error(websocket, exc.code, exc.reason)
                if exc.close:
                    await websocket.close(
                        code=PRESENCE_CLOSE_CODE,
                        reason="Presence payload is too large",
                    )
                    return
                continue
            
            # Handle different message types
            message_type = message.get("type")
            
            if message_type == "cell_update":
                await manager.send_personal_message(
                    websocket,
                    {
                        "type": "cell_update_rejected",
                        "reason": "Cell updates must be saved through the REST cell endpoint before broadcast.",
                    },
                )
            
            elif message_type in CURSOR_MESSAGE_TYPES:
                if not presence_rate_limiter.allow(user.id, sheet_id):
                    await _send_websocket_error(
                        websocket,
                        "rate_limited",
                        "Too many presence messages. Please slow down.",
                    )
                    await websocket.close(
                        code=PRESENCE_CLOSE_CODE,
                        reason="Presence message rate limit exceeded",
                    )
                    return

                try:
                    payload = _cursor_payload(message, user)
                except WebSocketPayloadError as exc:
                    await _send_websocket_error(websocket, exc.code, exc.reason)
                    continue

                await manager.broadcast_to_sheet(
                    sheet_id,
                    payload,
                    exclude=websocket
                )
            
            elif message_type == "selection":
                if not presence_rate_limiter.allow(user.id, sheet_id):
                    await _send_websocket_error(
                        websocket,
                        "rate_limited",
                        "Too many presence messages. Please slow down.",
                    )
                    await websocket.close(
                        code=PRESENCE_CLOSE_CODE,
                        reason="Presence message rate limit exceeded",
                    )
                    return

                try:
                    payload = _selection_payload(message, user)
                except WebSocketPayloadError as exc:
                    await _send_websocket_error(websocket, exc.code, exc.reason)
                    continue

                await manager.broadcast_to_sheet(
                    sheet_id,
                    payload,
                    exclude=websocket
                )
            
            elif message_type == "comment":
                await manager.send_personal_message(
                    websocket,
                    {
                        "type": "comment_rejected",
                        "reason": "Comments must be saved through the REST comment endpoint before broadcast.",
                    },
                )

            else:
                await _send_websocket_error(
                    websocket,
                    "unsupported_message_type",
                    "Unsupported WebSocket message type.",
                )

    except WebSocketDisconnect:
        pass

    except Exception:
        logger.exception("WebSocket error")

    finally:
        await _disconnect_and_notify(websocket, sheet_id)
