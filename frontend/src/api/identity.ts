import { API_URL } from './config';

export type UserSummary = {
  user_id: string;
  display_name: string;
};

export type BootstrapResponse = {
  token: string;
  user_id: string;
  device_id: string;
  display_name: string;
  other_users: UserSummary[];
};

export async function bootstrapIdentity(token: string | null): Promise<BootstrapResponse> {
  const response = await fetch(`${API_URL}/identity/bootstrap`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });

  if (!response.ok) {
    throw new Error(`Falha ao ligar ao servidor (${response.status})`);
  }

  return response.json();
}
