import { API_URL } from './config';

export async function getOrCreateConversation(
  userId: string,
  otherUserId: string,
): Promise<string> {
  const response = await fetch(`${API_URL}/conversations/with`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, other_user_id: otherUserId }),
  });

  if (!response.ok) {
    throw new Error(`Falha ao abrir a conversa (${response.status})`);
  }

  const data: { conversation_id: string } = await response.json();
  return data.conversation_id;
}
