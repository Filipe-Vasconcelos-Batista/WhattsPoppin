import { authFetch } from './session';

export type OneTimePrekeyInput = {
  key_id: number;
  public_key: string;
};

export type PublishKeysBody = {
  identityKey: string;
  signedPrekey: string;
  signedPrekeySignature: string;
  signedPrekeyId: number;
  oneTimePrekeys: OneTimePrekeyInput[];
};

export async function publishDeviceKeys(deviceId: string, keys: PublishKeysBody): Promise<void> {
  const response = await authFetch(`/devices/${deviceId}/keys`, {
    method: 'POST',
    body: JSON.stringify({
      identity_key: keys.identityKey,
      signed_prekey: keys.signedPrekey,
      signed_prekey_signature: keys.signedPrekeySignature,
      signed_prekey_id: keys.signedPrekeyId,
      one_time_prekeys: keys.oneTimePrekeys,
    }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail ?? `Erro do servidor (${response.status})`);
  }
}

export type PrekeyBundleResponse = {
  identity_key: string | null;
  signed_prekey: string | null;
  signed_prekey_signature: string | null;
  signed_prekey_id: number | null;
  one_time_prekey_id: number | null;
  one_time_prekey: string | null;
};

export async function fetchPrekeyBundle(deviceId: string): Promise<PrekeyBundleResponse> {
  const response = await authFetch(`/devices/${deviceId}/prekey-bundle`);
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail ?? `Erro do servidor (${response.status})`);
  }
  return response.json();
}
