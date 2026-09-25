import type { MessageStatus } from '../types/chat';

const ORDER: Record<MessageStatus, number> = {
  pending: 0,
  sent: 1,
  delivered: 2,
  read: 3,
};

// Recibos podem chegar fora de ordem (ex.: "delivered" depois de "read") -
// o estado só avança.
export function advanceStatus(
  current: MessageStatus | undefined,
  next: MessageStatus,
): MessageStatus {
  if (!current) return next;
  return ORDER[next] > ORDER[current] ? next : current;
}
