from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
import json

from app.core.database import get_db
from app.models.dataset import Sheet as SheetModel
from app.models.user import User
from app.services.websocket_manager import manager
from app.core.security import decode_token

router = APIRouter()


async def get_user_from_token(token: str, db: Session) -> User:
    """Get user from WebSocket token."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    return user


@router.websocket("/collaborate/{sheet_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    sheet_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time collaboration."""
    # Authenticate user
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    # Verify sheet exists and user has access
    sheet = db.query(SheetModel).filter(
        SheetModel.id == sheet_id,
        SheetModel.owner_id == user.id
    ).first()
    
    if not sheet:
        await websocket.close(code=1008, reason="Sheet not found")
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
            message = json.loads(data)
            
            # Handle different message types
            message_type = message.get("type")
            
            if message_type == "cell_update":
                # Broadcast cell update to other users
                await manager.broadcast_to_sheet(
                    sheet_id,
                    {
                        "type": "cell_update",
                        "user_id": user.id,
                        "username": user.username,
                        "row": message.get("row"),
                        "column": message.get("column"),
                        "value": message.get("value"),
                        "timestamp": message.get("timestamp")
                    },
                    exclude=websocket
                )
            
            elif message_type == "cursor_move":
                # Broadcast cursor position
                await manager.broadcast_to_sheet(
                    sheet_id,
                    {
                        "type": "cursor_move",
                        "user_id": user.id,
                        "username": user.username,
                        "row": message.get("row"),
                        "column": message.get("column")
                    },
                    exclude=websocket
                )
            
            elif message_type == "selection":
                # Broadcast selection
                await manager.broadcast_to_sheet(
                    sheet_id,
                    {
                        "type": "selection",
                        "user_id": user.id,
                        "username": user.username,
                        "start_row": message.get("start_row"),
                        "start_column": message.get("start_column"),
                        "end_row": message.get("end_row"),
                        "end_column": message.get("end_column")
                    },
                    exclude=websocket
                )
            
            elif message_type == "comment":
                # Broadcast comment
                await manager.broadcast_to_sheet(
                    sheet_id,
                    {
                        "type": "comment",
                        "user_id": user.id,
                        "username": user.username,
                        "row": message.get("row"),
                        "column": message.get("column"),
                        "text": message.get("text"),
                        "timestamp": message.get("timestamp")
                    },
                    exclude=websocket
                )
    
    except WebSocketDisconnect:
        info = manager.disconnect(websocket)
        if info:
            # Notify others that user left
            await manager.broadcast_to_sheet(
                sheet_id,
                {
                    "type": "user_left",
                    "user_id": info["user_id"],
                    "username": info["username"],
                    "active_users": len(manager.active_connections.get(sheet_id, []))
                }
            )
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)
