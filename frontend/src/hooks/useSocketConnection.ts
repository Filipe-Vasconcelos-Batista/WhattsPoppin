import { useEffect, useRef } from 'react';

import { WS_URL } from '../api/config';

// Fixo e simples - isto é só para o backend local reiniciar (--reload) sem
// teres de dar refresh à página. Não é a estratégia de retry federada a
// sério (essa é a do federation_outbox, com backoff exponencial).
const RECONNECT_DELAY_MS = 1500;

export function useSocketConnection(
  deviceId: string | null,
  onPayload: (payload: unknown) => void,
  onOpen?: () => void,
) {
  const socketRef = useRef<WebSocket | null>(null);
  const onPayloadRef = useRef(onPayload);
  const onOpenRef = useRef(onOpen);

  useEffect(() => {
    onPayloadRef.current = onPayload;
    onOpenRef.current = onOpen;
  });

  useEffect(() => {
    if (!deviceId) return;

    let cancelled = false;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      const socket = new WebSocket(`${WS_URL}/ws?device_id=${deviceId}`);
      socketRef.current = socket;
      socket.onopen = () => onOpenRef.current?.();
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

  // Fora de OPEN, o browser lança erro (CONNECTING) ou descarta em silêncio
  // (CLOSED). Aqui não se envia e devolve-se false - quem chama decide se
  // guarda para depois (a outbox guarda; os acks são reentregues ao religar).
  function send(payload: Record<string, unknown>): boolean {
    const socket = socketRef.current;
    if (socket?.readyState !== WebSocket.OPEN) return false;
    socket.send(JSON.stringify(payload));
    return true;
  }

  return { send };
}
