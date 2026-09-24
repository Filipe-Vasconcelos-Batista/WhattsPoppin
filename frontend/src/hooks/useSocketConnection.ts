import { useEffect, useRef } from 'react';

import { WS_URL } from '../api/config';

// Fixo e simples - isto é só para o backend local reiniciar (--reload) sem
// teres de dar refresh à página. Não é a estratégia de retry federada a
// sério (essa é a do federation_outbox, com backoff exponencial).
const RECONNECT_DELAY_MS = 1500;

export function useSocketConnection(
  deviceId: string | null,
  onPayload: (payload: unknown) => void,
) {
  const socketRef = useRef<WebSocket | null>(null);
  const onPayloadRef = useRef(onPayload);

  useEffect(() => {
    onPayloadRef.current = onPayload;
  });

  useEffect(() => {
    if (!deviceId) return;

    let cancelled = false;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      const socket = new WebSocket(`${WS_URL}/ws?device_id=${deviceId}`);
      socketRef.current = socket;
      socket.onmessage = (event) => onPayloadRef.current(JSON.parse(event.data));
      socket.onclose = () => {
        if (cancelled) return;
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
  }, [deviceId]);

  function send(payload: Record<string, unknown>) {
    socketRef.current?.send(JSON.stringify(payload));
  }

  return { send };
}
