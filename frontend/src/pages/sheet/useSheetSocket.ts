import { useEffect, useRef, useState } from 'react';
import type {
  ActiveUser,
  CommittedCellUpdate,
  CollaborationComment,
  CursorActivity,
} from './types';
import { sheetAPI } from '@/lib/api';

export function buildCollaborateUrl(sheetId: number, ticket: string) {
  const explicitWsUrl = import.meta.env.VITE_WS_URL;
  if (explicitWsUrl) {
    return `${explicitWsUrl.replace(/\/$/, '')}/ws/collaborate/${sheetId}?ticket=${encodeURIComponent(ticket)}`;
  }
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const wsBase = apiUrl.replace(/^http/, 'ws');
  return `${wsBase}/ws/collaborate/${sheetId}?ticket=${encodeURIComponent(ticket)}`;
}

export function parseCommittedCellUpdate(
  message: Record<string, unknown>
): CommittedCellUpdate | null {
  if (message.type !== 'cell_update') {
    return null;
  }
  const rowIndex = message.row_index ?? message.row;
  if (
    typeof rowIndex !== 'number' ||
    typeof message.column !== 'string' ||
    typeof message.version !== 'number'
  ) {
    return null;
  }

  return {
    user_id: typeof message.user_id === 'number' ? message.user_id : undefined,
    username: typeof message.username === 'string' ? message.username : undefined,
    row_index: rowIndex,
    column: message.column,
    value: message.value,
    formula:
      typeof message.formula === 'string' || message.formula === null
        ? message.formula
        : undefined,
    version: message.version,
    timestamp: typeof message.timestamp === 'string' ? message.timestamp : undefined,
  };
}

export function useSheetSocket(sheetId?: number) {
  const socketRef = useRef<WebSocket | null>(null);
  const [activeUsers, setActiveUsers] = useState<ActiveUser[]>([]);
  const [activeUserCount, setActiveUserCount] = useState(0);
  const [cursorActivity, setCursorActivity] = useState<CursorActivity | null>(null);
  const [realtimeComments, setRealtimeComments] = useState<CollaborationComment[]>([]);
  const [lastCellUpdate, setLastCellUpdate] = useState<CommittedCellUpdate | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'connecting' | 'open' | 'closed'>('idle');

  useEffect(() => {
    if (!sheetId) {
      setActiveUsers([]);
      setActiveUserCount(0);
      setLastCellUpdate(null);
      setConnectionStatus('idle');
      return;
    }

    let cancelled = false;
    let shouldReconnect = true;
    let reconnectTimer: number | undefined;
    let reconnectAttempt = 0;

    const resetPresence = () => {
      setActiveUsers([]);
      setActiveUserCount(0);
    };

    const connect = async () => {
      setConnectionStatus('connecting');
      try {
        const { ticket } = await sheetAPI.createWebSocketTicket(sheetId);
        if (cancelled) {
          return;
        }

        const socket = new WebSocket(buildCollaborateUrl(sheetId, ticket));
        socketRef.current = socket;
        socket.onopen = () => {
          reconnectAttempt = 0;
          setConnectionStatus('open');
        };
        socket.onmessage = (event) => {
          let message: Record<string, any>;
          try {
            message = JSON.parse(event.data);
          } catch {
            return;
          }
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
          if (message.type === 'cell_update') {
            const cellUpdate = parseCommittedCellUpdate(message);
            if (cellUpdate) {
              setLastCellUpdate(cellUpdate);
            }
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
          if (message.type === 'access_revoked') {
            shouldReconnect = false;
            resetPresence();
            setConnectionStatus('closed');
            socket.close();
          }
        };
        socket.onclose = () => {
          if (socketRef.current === socket) {
            socketRef.current = null;
          }
          resetPresence();
          setConnectionStatus('closed');
          if (!cancelled && shouldReconnect) {
            const delay = Math.min(1000 * 2 ** reconnectAttempt, 10000);
            reconnectAttempt += 1;
            reconnectTimer = window.setTimeout(connect, delay);
          }
        };
        socket.onerror = () => {
          setConnectionStatus('closed');
        };
      } catch (error: any) {
        resetPresence();
        setConnectionStatus('closed');
        const status = error?.response?.status;
        if (!cancelled && ![401, 403, 404].includes(status)) {
          const delay = Math.min(1000 * 2 ** reconnectAttempt, 10000);
          reconnectAttempt += 1;
          reconnectTimer = window.setTimeout(connect, delay);
        }
      }
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer !== undefined) {
        window.clearTimeout(reconnectTimer);
      }
      if (socketRef.current) {
        socketRef.current.close();
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
    lastCellUpdate,
    connectionStatus,
    sendSocketMessage,
  };
}
