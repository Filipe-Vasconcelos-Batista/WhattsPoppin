import { API_URL } from './config';

export async function updateDisplayName(token: string, displayName: string): Promise<string> {
  const response = await fetch(`${API_URL}/users/me/display_name`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, display_name: displayName }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail ?? `Erro do servidor (${response.status})`);
  }

  const data: { display_name: string } = await response.json();
  return data.display_name;
}
