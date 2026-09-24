import { API_URL } from './config';

export type UserSummary = {
  user_id: string;
  display_name: string;
};

export type AuthResponse = {
  token: string;
  user_id: string;
  device_id: string;
  display_name: string;
  other_users: UserSummary[];
};

async function postAuth(path: string, body: object): Promise<AuthResponse> {
  const response = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail ?? `Erro do servidor (${response.status})`);
  }

  return response.json();
}

export function registerUser(username: string, password: string): Promise<AuthResponse> {
  return postAuth('/auth/register', { username, password });
}

export function loginUser(username: string, password: string): Promise<AuthResponse> {
  return postAuth('/auth/login', { username, password });
}

export async function resumeSession(token: string): Promise<AuthResponse | null> {
  const response = await fetch(`${API_URL}/auth/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });

  if (!response.ok) return null;
  return response.json();
}
