import type { UserSummary } from './auth';
import { authFetch } from './session';

export type ContactStatus = 'pending_outgoing' | 'pending_incoming' | 'accepted';

export type ContactSummary = UserSummary & { status: ContactStatus };

async function errorFrom(response: Response): Promise<Error> {
  const data = await response.json().catch(() => null);
  return new Error(data?.detail ?? `Erro do servidor (${response.status})`);
}

export async function addContact(identifier: string): Promise<ContactSummary> {
  const response = await authFetch('/contacts', {
    method: 'POST',
    body: JSON.stringify({ identifier }),
  });
  if (!response.ok) throw await errorFrom(response);
  return response.json();
}

export async function acceptContact(userId: string): Promise<ContactSummary> {
  const response = await authFetch(`/contacts/${userId}/accept`, { method: 'POST' });
  if (!response.ok) throw await errorFrom(response);
  return response.json();
}

export async function removeContact(userId: string): Promise<void> {
  const response = await authFetch(`/contacts/${userId}`, { method: 'DELETE' });
  if (!response.ok) throw await errorFrom(response);
}
