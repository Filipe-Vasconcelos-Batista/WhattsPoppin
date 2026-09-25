// Persiste as sessões por par de dispositivos (o meu device, o device do
// outro) - não por conversa nem por utilizador, porque cada par de
// dispositivos tem a sua própria sessão.

import AsyncStorage from '@react-native-async-storage/async-storage';

import { type RatchetState } from './doubleRatchet';
import { type X3dhInitialMessage } from './x3dh';
import { bytesToBase64, base64ToBytes } from './encoding';

export interface SessionRecord {
  state: RatchetState;
  // Lado de Alice: prelúdio X3DH que vai em todas as mensagens até ela
  // decifrar a primeira resposta - se a primeira mensagem se perder, a
  // seguinte ainda consegue abrir a sessão do lado de Bob.
  pendingInitialMessage: X3dhInitialMessage | null;
  // Lado de Bob: EK de Alice que criou esta sessão - distingue um prelúdio
  // repetido (reutiliza a sessão) de uma sessão nova iniciada por Alice.
  initiatorEphemeralKey: Uint8Array | null;
}

function storageKey(myDeviceId: string, remoteDeviceId: string): string {
  return `whattspoppin.session.${myDeviceId}.${remoteDeviceId}`;
}

interface StoredState {
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

interface StoredInitialMessage {
  identityKey: string;
  ephemeralKey: string;
  signedPrekeyId: number;
  oneTimePrekeyId: number | null;
}

interface StoredSession {
  state: StoredState;
  pendingInitialMessage: StoredInitialMessage | null;
  initiatorEphemeralKey: string | null;
}

function toBase64OrNull(bytes: Uint8Array | null): string | null {
  return bytes ? bytesToBase64(bytes) : null;
}

function fromBase64OrNull(value: string | null): Uint8Array | null {
  return value ? base64ToBytes(value) : null;
}

function serializeState(state: RatchetState): StoredState {
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

function deserializeState(stored: StoredState): RatchetState {
  return {
    dhs: {
      privateKey: base64ToBytes(stored.dhsPrivateKey),
      publicKey: base64ToBytes(stored.dhsPublicKey),
    },
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

function serialize(record: SessionRecord): StoredSession {
  const pending = record.pendingInitialMessage;
  return {
    state: serializeState(record.state),
    pendingInitialMessage: pending
      ? {
          identityKey: bytesToBase64(pending.identityKey),
          ephemeralKey: bytesToBase64(pending.ephemeralKey),
          signedPrekeyId: pending.signedPrekeyId,
          oneTimePrekeyId: pending.oneTimePrekeyId,
        }
      : null,
    initiatorEphemeralKey: toBase64OrNull(record.initiatorEphemeralKey),
  };
}

function deserialize(stored: StoredSession): SessionRecord {
  const pending = stored.pendingInitialMessage;
  return {
    state: deserializeState(stored.state),
    pendingInitialMessage: pending
      ? {
          identityKey: base64ToBytes(pending.identityKey),
          ephemeralKey: base64ToBytes(pending.ephemeralKey),
          signedPrekeyId: pending.signedPrekeyId,
          oneTimePrekeyId: pending.oneTimePrekeyId,
        }
      : null,
    initiatorEphemeralKey: fromBase64OrNull(stored.initiatorEphemeralKey),
  };
}

export async function saveSession(
  myDeviceId: string,
  remoteDeviceId: string,
  record: SessionRecord,
): Promise<void> {
  await AsyncStorage.setItem(
    storageKey(myDeviceId, remoteDeviceId),
    JSON.stringify(serialize(record)),
  );
}

export async function loadSession(
  myDeviceId: string,
  remoteDeviceId: string,
): Promise<SessionRecord | null> {
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
