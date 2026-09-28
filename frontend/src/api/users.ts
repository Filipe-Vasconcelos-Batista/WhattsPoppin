import { authFetch } from './session';

export async function updateDisplayName(displayName: string): Promise<string> {
  const response = await authFetch('/users/me/display_name', {
    method: 'PATCH',
    body: JSON.stringify({ display_name: displayName }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail ?? `Erro do servidor (${response.status})`);
  }

  const data: { display_name: string } = await response.json();
  return data.display_name;
}
