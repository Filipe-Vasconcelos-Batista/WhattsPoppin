import AsyncStorage from '@react-native-async-storage/async-storage';
import { ed25519 } from '@noble/curves/ed25519.js';

import { generateKeyPair, type KeyPair } from './primitives';
import { bytesToBase64, base64ToBytes } from './encoding';
import { publishDeviceKeys } from '../api/devices';

export const ONE_TIME_PREKEY_BATCH_SIZE = 20;
const MAX_KEY_ID = 0x7fffffff; // cabe num IntegerField de 32 bits com sinal

function randomKeyId(): number {
  return Math.floor(Math.random() * MAX_KEY_ID);
}

export interface OneTimePrekeyMaterial {
  keyId: number;
  keyPair: KeyPair; // X25519
}

export function generateOneTimePrekeys(count: number): OneTimePrekeyMaterial[] {
  return Array.from({ length: count }, () => ({
    keyId: randomKeyId(),
    keyPair: generateKeyPair(),
  }));
}

export interface DeviceKeyMaterial {
  identityKey: KeyPair; // Ed25519 (usa a mesma forma {privateKey, publicKey})
  signedPrekey: KeyPair; // X25519
  signedPrekeyId: number;
  signedPrekeySignature: Uint8Array; // Ed25519, assina signedPrekey.publicKey
  oneTimePrekeys: OneTimePrekeyMaterial[];
}

export function generateDeviceKeys(): DeviceKeyMaterial {
  const ik = ed25519.keygen();
  const signedPrekey = generateKeyPair();
  const signedPrekeyId = 1;
  const signedPrekeySignature = ed25519.sign(signedPrekey.publicKey, ik.secretKey);

  return {
    identityKey: { privateKey: ik.secretKey, publicKey: ik.publicKey },
    signedPrekey,
    signedPrekeyId,
    signedPrekeySignature,
    oneTimePrekeys: generateOneTimePrekeys(ONE_TIME_PREKEY_BATCH_SIZE),
  };
}

function storageKey(deviceId: string): string {
  return `whattspoppin.device_keys.${deviceId}`;
}

interface StoredOneTimePrekey {
  keyId: number;
  privateKey: string; // base64
}

interface StoredDeviceKeys {
  identityPrivateKey: string; // base64, Ed25519
  identityPublicKey: string;
  signedPrekeyPrivateKey: string; // base64, X25519
  signedPrekeyPublicKey: string;
  signedPrekeyId: number;
  // Só as privadas - a pública de cada OPK já foi publicada. A privada
  // fica para a Fase 3 (X3DH) consumir e depois apagar do storage.
  oneTimePrekeys: StoredOneTimePrekey[];
}

export async function loadDeviceKeys(deviceId: string): Promise<StoredDeviceKeys | null> {
  const raw = await AsyncStorage.getItem(storageKey(deviceId));
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredDeviceKeys;
  } catch {
    return null;
  }
}

// Guarda chaves novas, fazendo merge com quaisquer OPKs locais já
// existentes (nunca as substitui) - identidade/SPK são sempre as mais
// recentes passadas (não há noção de "manter a antiga" para essas, só
// rodam por decisão explícita, fora do âmbito desta fase).
export async function storeDeviceKeys(deviceId: string, keys: DeviceKeyMaterial): Promise<void> {
  const existing = await loadDeviceKeys(deviceId);
  const newOneTimePrekeys: StoredOneTimePrekey[] = keys.oneTimePrekeys.map(
    ({ keyId, keyPair }) => ({
      keyId,
      privateKey: bytesToBase64(keyPair.privateKey),
    }),
  );

  const stored: StoredDeviceKeys = {
    identityPrivateKey: bytesToBase64(keys.identityKey.privateKey),
    identityPublicKey: bytesToBase64(keys.identityKey.publicKey),
    signedPrekeyPrivateKey: bytesToBase64(keys.signedPrekey.privateKey),
    signedPrekeyPublicKey: bytesToBase64(keys.signedPrekey.publicKey),
    signedPrekeyId: keys.signedPrekeyId,
    oneTimePrekeys: [...(existing?.oneTimePrekeys ?? []), ...newOneTimePrekeys],
  };
  await AsyncStorage.setItem(storageKey(deviceId), JSON.stringify(stored));
}

export async function consumeOneTimePrekey(
  deviceId: string,
  keyId: number,
): Promise<Uint8Array | null> {
  const stored = await loadDeviceKeys(deviceId);
  if (!stored) return null;

  const index = stored.oneTimePrekeys.findIndex((opk) => opk.keyId === keyId);
  if (index === -1) return null;

  const [match] = stored.oneTimePrekeys.splice(index, 1);
  await AsyncStorage.setItem(storageKey(deviceId), JSON.stringify(stored));
  return base64ToBytes(match.privateKey);
}

// Gera um lote novo, guarda as privadas localmente (merge) e publica as
// públicas. Chamado uma vez por register()/login() (cada um cria sempre
// um Device novo - ver nota em IdentityContext.tsx), nunca em
// resumeSession() - mas seguro para chamar de novo no futuro (reposição
// de OPKs) sem perder chaves privadas ainda não consumidas.
export async function generateAndPublishDeviceKeys(
  deviceId: string,
  clientToken: string,
): Promise<void> {
  const keys = generateDeviceKeys();
  await storeDeviceKeys(deviceId, keys);
  await publishDeviceKeys(deviceId, clientToken, {
    identityKey: bytesToBase64(keys.identityKey.publicKey),
    signedPrekey: bytesToBase64(keys.signedPrekey.publicKey),
    signedPrekeySignature: bytesToBase64(keys.signedPrekeySignature),
    signedPrekeyId: keys.signedPrekeyId,
    oneTimePrekeys: keys.oneTimePrekeys.map(({ keyId, keyPair }) => ({
      key_id: keyId,
      public_key: bytesToBase64(keyPair.publicKey),
    })),
  });
}
