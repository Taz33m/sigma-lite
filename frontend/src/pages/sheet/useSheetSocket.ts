import { useEffect, useRef, useState } from 'react';
import type {
  ActiveUser,
  CollaborationComment,
  CursorActivity,
} from './types';

function buildCollaborateUrl(sheetId: number, token: string) {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const wsBase = apiUrl.replace(/^http/, 'ws');
  return `${wsBase}/ws/collaborate/${sheetId}?token=${encodeURIComponent(token)}`;
}

export function useSheetSocket(sheetId?: number) {
  const socketRef = useRef<WebSocket | null>(null);
  const [activeUsers, setActiveUsers] = useState<ActiveUser[]>([]);
  const [activeUserCount, setActiveUserCount] = useState(0);
  const [cursorActivity, setCursorActivity] = useState<CursorActivity | null>(null);
  const [realtimeComments, setRealtimeComments] = useState<CollaborationComment[]>([]);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!sheetId || !token) {
      setActiveUsers([]);
      setActiveUserCount(0);
      return;
    }

    const socket = new WebSocket(buildCollaborateUrl(sheetId, token));
    socketRef.current = socket;
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (Array.isArray(message.active_users)) {
        setActiveUsers(message.active_users);
        setActiveUserCount(message.active_users.length);
      } else if (typeof message.active_users === 'number') {
        setActiveUserCount(message.active_users);
      }
      if (message.type === 'cursor_move') {
        setCursorActivity({
          username: message.username,
          row: message.row,
          column: message.column,
        });
      }
      if (message.type === 'comment') {
        setRealtimeComments((current) => {
          const exists = current.some(
            (comment) =>
              comment.id === message.id ||
              (comment.timestamp === message.timestamp && comment.text === message.text)
          );
          if (exists) {
            return current;
          }
          return [
            ...current,
            {
              id: message.id,
              username: message.username || 'Collaborator',
              text: message.text || '',
              timestamp: message.timestamp,
              row_index: message.row_index,
              column: message.column,
            },
          ];
        });
      }
    };
    socket.onclose = () => {
      setActiveUsers([]);
      setActiveUserCount(0);
    };

    return () => {
      socket.close();
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
    };
  }, [sheetId]);

  const sendSocketMessage = (message: Record<string, unknown>) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    }
  };

  return {
    activeUsers,
    activeUserCount,
    cursorActivity,
    realtimeComments,
    sendSocketMessage,
  };
}
