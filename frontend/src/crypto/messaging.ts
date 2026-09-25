// Liga as camadas de cifra ao transporte: decide quando abrir sessão (X3DH)
// e quando reutilizá-la, cifra/decifra com o Double Ratchet, persiste as
// sessões e converte tudo para o formato que viaja no WebSocket (base64).

import { fetchRecipientDevices } from '../api/conversations';
import {
  initAlice,
  initBob,
  ratchetDecrypt,
  ratchetEncrypt,
  type RatchetHeader,
} from './doubleRatchet';
import { bytesToBase64, base64ToBytes } from './encoding';
import { consumeOneTimePrekey, loadDeviceKeys } from './keys';
import { loadSession, saveSession, type SessionRecord } from './sessionStore';
import { initiateSession, receiveInitialMessage, type X3dhInitialMessage } from './x3dh';

export interface WireHeader {
  dh: string;
  pn: number;
  n: number;
}

export interface WireX3dh {
  identity_key: string;
  ephemeral_key: string;
  signed_prekey_id: number;
  one_time_prekey_id: number | null;
}

export interface WireEnvelope {
  device_id: string;
  header: WireHeader;
  ciphertext: string;
  x3dh: WireX3dh | null;
}

export interface IncomingEncryptedMessage {
  header: WireHeader;
  ciphertext: string;
  x3dh: WireX3dh | null;
}

// Todas as operações de cifra passam por aqui, uma de cada vez: cada uma lê
// e grava a sessão, e duas em paralelo leriam o mesmo estado e uma escrita
// apagaria a outra. Também preserva a ordem de chegada do WebSocket.
let queue: Promise<unknown> = Promise.resolve();

export function runSerially<T>(task: () => Promise<T>): Promise<T> {
  const result = queue.then(task);
  queue = result.catch(() => undefined);
  return result;
}

function bytesEqual(a: Uint8Array, b: Uint8Array): boolean {
  return a.length === b.length && a.every((byte, i) => byte === b[i]);
}

function toWireHeader(header: RatchetHeader): WireHeader {
  return { dh: bytesToBase64(header.dh), pn: header.pn, n: header.n };
}

function fromWireHeader(header: WireHeader): RatchetHeader {
  return { dh: base64ToBytes(header.dh), pn: header.pn, n: header.n };
}

function toWireX3dh(message: X3dhInitialMessage): WireX3dh {
  return {
    identity_key: bytesToBase64(message.identityKey),
    ephemeral_key: bytesToBase64(message.ephemeralKey),
    signed_prekey_id: message.signedPrekeyId,
    one_time_prekey_id: message.oneTimePrekeyId,
  };
}

function fromWireX3dh(prelude: WireX3dh): X3dhInitialMessage {
  return {
    identityKey: base64ToBytes(prelude.identity_key),
    ephemeralKey: base64ToBytes(prelude.ephemeral_key),
    signedPrekeyId: prelude.signed_prekey_id,
    oneTimePrekeyId: prelude.one_time_prekey_id,
  };
}

// Sem fila - quem chama tem de estar dentro de runSerially.
export async function encryptForDevice(
  myDeviceId: string,
  remoteDeviceId: string,
  text: string,
): Promise<WireEnvelope> {
  let record = await loadSession(myDeviceId, remoteDeviceId);
  if (!record) {
    const x3dh = await initiateSession({ myDeviceId, recipientDeviceId: remoteDeviceId });
    record = {
      state: initAlice(x3dh.sharedKey, x3dh.remoteRatchetKey, x3dh.associatedData),
      pendingInitialMessage: x3dh.initialMessage,
      initiatorEphemeralKey: null,
    };
  }

  const { state, header, ciphertext } = ratchetEncrypt(
    record.state,
    new TextEncoder().encode(text),
  );
  await saveSession(myDeviceId, remoteDeviceId, { ...record, state });

  return {
    device_id: remoteDeviceId,
    header: toWireHeader(header),
    ciphertext: bytesToBase64(ciphertext),
    x3dh: record.pendingInitialMessage ? toWireX3dh(record.pendingInitialMessage) : null,
  };
}

async function sessionFromPrelude(
  myDeviceId: string,
  prelude: X3dhInitialMessage,
): Promise<SessionRecord> {
  const responder = await receiveInitialMessage({
    myDeviceId,
    initialMessage: prelude,
    consumeOneTimePrekey: false,
  });
  const myKeys = await loadDeviceKeys(myDeviceId);
  if (!myKeys) throw new Error('Chaves locais não encontradas');

  // O par ratchet inicial de Bob é a sua signed prekey
  const signedPrekey = {
    privateKey: base64ToBytes(myKeys.signedPrekeyPrivateKey),
    publicKey: base64ToBytes(myKeys.signedPrekeyPublicKey),
  };
  return {
    state: initBob(responder.sharedKey, signedPrekey, responder.associatedData),
    pendingInitialMessage: null,
    initiatorEphemeralKey: prelude.ephemeralKey,
  };
}

// Sem fila - quem chama tem de estar dentro de runSerially.
export async function decryptFromDevice(
  myDeviceId: string,
  senderDeviceId: string,
  message: IncomingEncryptedMessage,
): Promise<string> {
  const existing = await loadSession(myDeviceId, senderDeviceId);
  const prelude = message.x3dh ? fromWireX3dh(message.x3dh) : null;

  // Prelúdio com uma EK que ainda não conhecemos = Alice abriu uma sessão
  // nova (ou é a primeira). Com a mesma EK = só a repetição habitual até
  // respondermos, reutiliza-se a sessão que já existe.
  const newSessionPrelude =
    prelude &&
    !(
      existing?.initiatorEphemeralKey &&
      bytesEqual(existing.initiatorEphemeralKey, prelude.ephemeralKey)
    )
      ? prelude
      : null;

  const record = newSessionPrelude
    ? await sessionFromPrelude(myDeviceId, newSessionPrelude)
    : existing;
  if (!record) {
    throw new Error('Não há sessão com este dispositivo e a mensagem não traz prelúdio X3DH');
  }

  const { state, plaintext } = ratchetDecrypt(
    record.state,
    fromWireHeader(message.header),
    base64ToBytes(message.ciphertext),
  );

  // Só depois de decifrar com sucesso: gastar a OPK e gravar a sessão.
  if (newSessionPrelude && newSessionPrelude.oneTimePrekeyId !== null) {
    await consumeOneTimePrekey(myDeviceId, newSessionPrelude.oneTimePrekeyId);
  }
  // Decifrar uma mensagem do outro lado = ele já tem a sessão, deixa de ser
  // preciso repetir o prelúdio.
  await saveSession(myDeviceId, senderDeviceId, { ...record, state, pendingInitialMessage: null });

  return new TextDecoder().decode(plaintext);
}

// Cifra uma mensagem para todos os dispositivos do destinatário. Um device
// que falhe (ex.: bundle inválido) não impede os outros.
export function encryptForConversation(
  myDeviceId: string,
  conversationId: string,
  text: string,
): Promise<WireEnvelope[]> {
  return runSerially(async () => {
    const deviceIds = await fetchRecipientDevices(conversationId, myDeviceId);
    const envelopes: WireEnvelope[] = [];
    for (const deviceId of deviceIds) {
      try {
        envelopes.push(await encryptForDevice(myDeviceId, deviceId, text));
      } catch (error) {
        console.warn(`Falha ao cifrar para o dispositivo ${deviceId}:`, error);
      }
    }
    return envelopes;
  });
}

export function decryptIncoming(
  myDeviceId: string,
  senderDeviceId: string,
  message: IncomingEncryptedMessage,
): Promise<string> {
  return runSerially(() => decryptFromDevice(myDeviceId, senderDeviceId, message));
}
