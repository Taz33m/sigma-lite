from typing import Dict, Set
from fastapi import WebSocket
import json


class ConnectionManager:
    """Manage WebSocket connections for real-time collaboration."""
    
    def __init__(self):
        # Map sheet_id to set of active connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Map websocket to user info
        self.connection_info: Dict[WebSocket, dict] = {}
    
    async def connect(self, websocket: WebSocket, sheet_id: int, user_id: int, username: str):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        if sheet_id not in self.active_connections:
            self.active_connections[sheet_id] = set()
        
        self.active_connections[sheet_id].add(websocket)
        self.connection_info[websocket] = {
            "user_id": user_id,
            "username": username,
            "sheet_id": sheet_id
        }
        
        # Notify others that a user joined
        await self.broadcast_to_sheet(
            sheet_id,
            {
                "type": "user_joined",
                "user_id": user_id,
                "username": username,
                "active_users": len(self.active_connections[sheet_id])
            },
            exclude=websocket
        )
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.connection_info:
            info = self.connection_info[websocket]
            sheet_id = info["sheet_id"]
            
            if sheet_id in self.active_connections:
                self.active_connections[sheet_id].discard(websocket)
                
                # Clean up empty sheet rooms
                if not self.active_connections[sheet_id]:
                    del self.active_connections[sheet_id]
            
            del self.connection_info[websocket]
            
            return info
        return None
    
    async def broadcast_to_sheet(self, sheet_id: int, message: dict, exclude: WebSocket = None):
        """Broadcast a message to all connections in a sheet."""
        if sheet_id not in self.active_connections:
            return
        
        disconnected = []
        message_str = json.dumps(message)
        
        for connection in self.active_connections[sheet_id]:
            if connection == exclude:
                continue
            
            try:
                await connection.send_text(message_str)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """Send a message to a specific connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception:
            self.disconnect(websocket)
    
    def get_active_users(self, sheet_id: int) -> list:
        """Get list of active users in a sheet."""
        if sheet_id not in self.active_connections:
            return []
        
        users = []
        for connection in self.active_connections[sheet_id]:
            if connection in self.connection_info:
                info = self.connection_info[connection]
                users.append({
                    "user_id": info["user_id"],
                    "username": info["username"]
                })
        
        return users


# Global connection manager instance
manager = ConnectionManager()
