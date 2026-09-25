// Persiste o estado do Double Ratchet por par de dispositivos (o meu
// device, o device do outro) - não por conversa nem por utilizador, porque
// cada par de dispositivos tem a sua própria sessão.

import AsyncStorage from '@react-native-async-storage/async-storage';

import { type RatchetState } from './doubleRatchet';
import { bytesToBase64, base64ToBytes } from './encoding';

function storageKey(myDeviceId: string, remoteDeviceId: string): string {
  return `whattspoppin.session.${myDeviceId}.${remoteDeviceId}`;
}

interface StoredSession {
  dhsPrivateKey: string;
  dhsPublicKey: string;
  dhr: string | null;
  rk: string;
  cks: string | null;
  ckr: string | null;
  ns: number;
  nr: number;
  pn: number;
  skipped: [string, string][]; // [`${b64(dh)}:${n}`, mk em base64]
  ad: string;
}

function toBase64OrNull(bytes: Uint8Array | null): string | null {
  return bytes ? bytesToBase64(bytes) : null;
}

function fromBase64OrNull(value: string | null): Uint8Array | null {
  return value ? base64ToBytes(value) : null;
}

function serialize(state: RatchetState): StoredSession {
  return {
    dhsPrivateKey: bytesToBase64(state.dhs.privateKey),
    dhsPublicKey: bytesToBase64(state.dhs.publicKey),
    dhr: toBase64OrNull(state.dhr),
    rk: bytesToBase64(state.rk),
    cks: toBase64OrNull(state.cks),
    ckr: toBase64OrNull(state.ckr),
    ns: state.ns,
    nr: state.nr,
    pn: state.pn,
    skipped: [...state.skipped].map(([key, mk]) => [key, bytesToBase64(mk)]),
    ad: bytesToBase64(state.ad),
  };
}

function deserialize(stored: StoredSession): RatchetState {
  return {
    dhs: { privateKey: base64ToBytes(stored.dhsPrivateKey), publicKey: base64ToBytes(stored.dhsPublicKey) },
    dhr: fromBase64OrNull(stored.dhr),
    rk: base64ToBytes(stored.rk),
    cks: fromBase64OrNull(stored.cks),
    ckr: fromBase64OrNull(stored.ckr),
    ns: stored.ns,
    nr: stored.nr,
    pn: stored.pn,
    skipped: new Map(stored.skipped.map(([key, mk]) => [key, base64ToBytes(mk)])),
    ad: base64ToBytes(stored.ad),
  };
}

export async function saveSession(
  myDeviceId: string,
  remoteDeviceId: string,
  state: RatchetState,
): Promise<void> {
  await AsyncStorage.setItem(storageKey(myDeviceId, remoteDeviceId), JSON.stringify(serialize(state)));
}

export async function loadSession(myDeviceId: string, remoteDeviceId: string): Promise<RatchetState | null> {
  const raw = await AsyncStorage.getItem(storageKey(myDeviceId, remoteDeviceId));
  if (!raw) return null;
  try {
    return deserialize(JSON.parse(raw) as StoredSession);
  } catch {
    return null;
  }
}

export async function deleteSession(myDeviceId: string, remoteDeviceId: string): Promise<void> {
  await AsyncStorage.removeItem(storageKey(myDeviceId, remoteDeviceId));
}
