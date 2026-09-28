import { useEffect, useRef } from 'react';

import { WS_URL } from '../api/config';
const RECONNECT_DELAY_MS = 1500;
const CLOSE_UNAUTHORIZED = 4401;

type SocketCallbacks = {
  onOpen?: () => void;
  onUnauthorized?: () => void;
};

export function useSocketConnection(
  token: string | null,
  onPayload: (payload: unknown) => void,
  callbacks: SocketCallbacks = {},
) {
  const socketRef = useRef<WebSocket | null>(null);
  const authenticatedRef = useRef(false);
  const onPayloadRef = useRef(onPayload);
  const callbacksRef = useRef(callbacks);

  useEffect(() => {
    onPayloadRef.current = onPayload;
    callbacksRef.current = callbacks;
  });

  useEffect(() => {
    if (!token) return;

    let cancelled = false;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      const socket = new WebSocket(`${WS_URL}/ws`);
      socketRef.current = socket;
      authenticatedRef.current = false;
      socket.onopen = () => socket.send(JSON.stringify({ type: 'auth', token }));
      socket.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        if (!authenticatedRef.current) {
          if (payload?.type !== 'auth_ok') return;
          authenticatedRef.current = true;
          callbacksRef.current.onOpen?.();
          return;
        }
        onPayloadRef.current(payload);
      };
      socket.onclose = (event) => {
        authenticatedRef.current = false;
        if (cancelled) return;
        if (event.code === CLOSE_UNAUTHORIZED) {
          callbacksRef.current.onUnauthorized?.();
          return;
        }
        reconnectTimeout = setTimeout(connect, RECONNECT_DELAY_MS);
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [token]);

  // Fora de OPEN (ou antes do auth_ok), o browser lança erro (CONNECTING),
  // descarta em silêncio (CLOSED) ou o servidor fecha a ligação por falta de
  // auth. Aqui não se envia e devolve-se false - quem chama decide se guarda
  // para depois (a outbox guarda; os acks são reentregues ao religar).
  function send(payload: Record<string, unknown>): boolean {
    const socket = socketRef.current;
    if (socket?.readyState !== WebSocket.OPEN || !authenticatedRef.current) return false;
    socket.send(JSON.stringify(payload));
    return true;
  }

  return { send };
}
