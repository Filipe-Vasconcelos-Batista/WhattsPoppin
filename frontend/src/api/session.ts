import { API_URL } from './config';

let sessionToken: string | null = null;

export function setSessionToken(token: string | null): void {
  sessionToken = token;
}

export function bearer(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  if (!sessionToken) throw new Error('Sem sessão');
  return fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init.headers,
      ...bearer(sessionToken),
    },
  });
}
