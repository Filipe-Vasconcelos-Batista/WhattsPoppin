import { authFetch } from './session';

export async function getOrCreateConversation(otherUserId: string): Promise<string> {
  const response = await authFetch('/conversations/with', {
    method: 'POST',
    body: JSON.stringify({ other_user_id: otherUserId }),
  });

  if (!response.ok) {
    throw new Error(`Falha ao abrir a conversa (${response.status})`);
  }

  const data: { conversation_id: string } = await response.json();
  return data.conversation_id;
}

export async function fetchRecipientDevices(conversationId: string): Promise<string[]> {
  const response = await authFetch(`/conversations/${conversationId}/devices`);

  if (!response.ok) {
    throw new Error(`Falha ao obter os dispositivos da conversa (${response.status})`);
  }

  const data: { device_ids: string[] } = await response.json();
  return data.device_ids;
}
