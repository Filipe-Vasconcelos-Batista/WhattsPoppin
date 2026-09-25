// X3DH (Extended Triple Diffie-Hellman) - https://signal.org/docs/specifications/x3dh/
//
// Alice inicia sessão com Bob usando o bundle de chaves que ele já publicou
// (Fase 2). Ambos os lados chegam à mesma SK sem nunca a transmitir. Esta
// fase para aqui: SK vira a root key inicial do Double Ratchet (Fase 4) e
// só na Fase 5 isto se liga ao envio real de mensagens.

import { ed25519 } from '@noble/curves/ed25519.js';
import { concatBytes } from '@noble/hashes/utils.js';

import {
  KEY_LENGTH,
  type KeyPair,
  generateKeyPair,
  dh,
  edPublicKeyToX25519,
  edPrivateKeyToX25519,
  kdfX3dh,
} from './primitives';
import { loadDeviceKeys, consumeOneTimePrekey } from './keys';
import { fetchPrekeyBundle } from '../api/devices';
import { base64ToBytes } from './encoding';

// Mitigação recomendada pela spec do X3DH para quando a identity key
// também é usada fora do DH (aqui: para assinar a signed prekey) - separa
// esse uso do uso como chave Ed25519 "normal".
const KEY_REUSE_PREFIX = new Uint8Array(KEY_LENGTH).fill(0xff);

export class SignedPrekeySignatureError extends Error {
  constructor() {
    super('Assinatura da signed prekey inválida - o bundle pode ter sido adulterado');
    this.name = 'SignedPrekeySignatureError';
  }
}

// Bundle público de Bob, já descodificado de base64.
export interface X3dhBundle {
  identityKey: Uint8Array; // Ed25519 pub, IK_B
  signedPrekey: Uint8Array; // X25519 pub, SPK_B
  signedPrekeySignature: Uint8Array; // Ed25519 sig sobre signedPrekey
  signedPrekeyId: number;
  oneTimePrekey: Uint8Array | null; // X25519 pub, OPK_B - null se o pool estiver esgotado
  oneTimePrekeyId: number | null;
}

// O que Alice manda a Bob para ele reconstruir a SK. Sem ciphertext ainda -
// isso liga-se ao Double Ratchet, fora do âmbito desta fase.
export interface X3dhInitialMessage {
  identityKey: Uint8Array; // Ed25519 pub, IK_A
  ephemeralKey: Uint8Array; // X25519 pub, EK_A
  signedPrekeyId: number; // qual SPK de Bob foi usada
  oneTimePrekeyId: number | null; // qual OPK de Bob foi usada, se alguma
}

export interface X3dhInitiatorResult {
  sharedKey: Uint8Array; // SK, 32 bytes
  associatedData: Uint8Array; // AD = IK_A || IK_B
  remoteRatchetKey: Uint8Array; // SPK_B - chave ratchet inicial de Bob no Double Ratchet
  initialMessage: X3dhInitialMessage;
}

export interface X3dhResponderResult {
  sharedKey: Uint8Array;
  associatedData: Uint8Array; // AD = IK_A || IK_B, igual ao de Alice
}

function combineDhOutputs(dh1: Uint8Array, dh2: Uint8Array, dh3: Uint8Array, dh4: Uint8Array | null): Uint8Array {
  return dh4
    ? concatBytes(KEY_REUSE_PREFIX, dh1, dh2, dh3, dh4)
    : concatBytes(KEY_REUSE_PREFIX, dh1, dh2, dh3);
}

// Lado de Alice: verifica a assinatura da SPK de Bob, faz os 4 DHs (ou 3 se
// não houver OPK) e deriva a SK. Puro - sem I/O, testável diretamente.
export function deriveInitiatorSharedKey(
  aliceIdentityKey: KeyPair, // Ed25519
  aliceEphemeralKey: KeyPair, // X25519, fresca, uso único
  bobBundle: X3dhBundle,
): X3dhInitiatorResult {
  const validSignature = ed25519.verify(
    bobBundle.signedPrekeySignature,
    bobBundle.signedPrekey,
    bobBundle.identityKey,
  );
  if (!validSignature) throw new SignedPrekeySignatureError();

  const aliceIkX = edPrivateKeyToX25519(aliceIdentityKey.privateKey);
  const bobIkX = edPublicKeyToX25519(bobBundle.identityKey);

  const dh1 = dh(aliceIkX, bobBundle.signedPrekey); // IK_A x SPK_B
  const dh2 = dh(aliceEphemeralKey.privateKey, bobIkX); // EK_A x IK_B
  const dh3 = dh(aliceEphemeralKey.privateKey, bobBundle.signedPrekey); // EK_A x SPK_B
  const dh4 = bobBundle.oneTimePrekey ? dh(aliceEphemeralKey.privateKey, bobBundle.oneTimePrekey) : null; // EK_A x OPK_B

  return {
    sharedKey: kdfX3dh(combineDhOutputs(dh1, dh2, dh3, dh4)),
    associatedData: concatBytes(aliceIdentityKey.publicKey, bobBundle.identityKey),
    remoteRatchetKey: bobBundle.signedPrekey,
    initialMessage: {
      identityKey: aliceIdentityKey.publicKey,
      ephemeralKey: aliceEphemeralKey.publicKey,
      signedPrekeyId: bobBundle.signedPrekeyId,
      oneTimePrekeyId: bobBundle.oneTimePrekeyId,
    },
  };
}

// Chaves locais de Bob necessárias para responder a uma mensagem inicial.
// oneTimePrekeyPrivate é só Uint8Array (não KeyPair) porque o storage só
// guarda a privada de cada OPK - a pública nunca é persistida localmente.
export interface X3dhResponderLocalKeys {
  identityKey: KeyPair; // Ed25519, a própria IK de Bob
  signedPrekeyPrivate: Uint8Array; // X25519, corresponde a initialMessage.signedPrekeyId
  oneTimePrekeyPrivate: Uint8Array | null; // X25519, corresponde a oneTimePrekeyId (ou null)
}

// Lado de Bob: o espelho de deriveInitiatorSharedKey. Puro - sem I/O.
export function deriveResponderSharedKey(
  bobLocalKeys: X3dhResponderLocalKeys,
  initialMessage: X3dhInitialMessage,
): X3dhResponderResult {
  const wantsOpk = initialMessage.oneTimePrekeyId !== null;
  if (wantsOpk && !bobLocalKeys.oneTimePrekeyPrivate) {
    throw new Error('Mensagem inicial refere uma one-time prekey que já não existe localmente');
  }

  const bobIkX = edPrivateKeyToX25519(bobLocalKeys.identityKey.privateKey);
  const aliceIkX = edPublicKeyToX25519(initialMessage.identityKey);

  const dh1 = dh(bobLocalKeys.signedPrekeyPrivate, aliceIkX); // SPK_B x IK_A
  const dh2 = dh(bobIkX, initialMessage.ephemeralKey); // IK_B x EK_A
  const dh3 = dh(bobLocalKeys.signedPrekeyPrivate, initialMessage.ephemeralKey); // SPK_B x EK_A
  const dh4 = bobLocalKeys.oneTimePrekeyPrivate
    ? dh(bobLocalKeys.oneTimePrekeyPrivate, initialMessage.ephemeralKey) // OPK_B x EK_A
    : null;

  return {
    sharedKey: kdfX3dh(combineDhOutputs(dh1, dh2, dh3, dh4)),
    associatedData: concatBytes(initialMessage.identityKey, bobLocalKeys.identityKey.publicKey),
  };
}

export interface InitiateSessionParams {
  myDeviceId: string; // Alice - carrega as chaves locais dela
  recipientDeviceId: string; // Bob - vai buscar o bundle dele ao servidor
}

// Wrapper de I/O do lado de Alice: carrega as chaves locais, pede o bundle
// de Bob, gera a EK efémera e chama o núcleo puro.
export async function initiateSession(params: InitiateSessionParams): Promise<X3dhInitiatorResult> {
  const myKeys = await loadDeviceKeys(params.myDeviceId);
  if (!myKeys) throw new Error('Chaves locais não encontradas - gera as chaves primeiro');

  const aliceIdentityKey: KeyPair = {
    privateKey: base64ToBytes(myKeys.identityPrivateKey),
    publicKey: base64ToBytes(myKeys.identityPublicKey),
  };

  const raw = await fetchPrekeyBundle(params.recipientDeviceId);
  if (!raw.identity_key || !raw.signed_prekey || !raw.signed_prekey_signature || raw.signed_prekey_id === null) {
    throw new Error('O destinatário ainda não publicou as suas chaves');
  }

  const bobBundle: X3dhBundle = {
    identityKey: base64ToBytes(raw.identity_key),
    signedPrekey: base64ToBytes(raw.signed_prekey),
    signedPrekeySignature: base64ToBytes(raw.signed_prekey_signature),
    signedPrekeyId: raw.signed_prekey_id,
    oneTimePrekey: raw.one_time_prekey ? base64ToBytes(raw.one_time_prekey) : null,
    oneTimePrekeyId: raw.one_time_prekey_id,
  };

  const ephemeralKey = generateKeyPair(); // EK_A - fresca, uso único, nunca persistida
  return deriveInitiatorSharedKey(aliceIdentityKey, ephemeralKey, bobBundle);
}

export interface ReceiveInitialMessageParams {
  myDeviceId: string; // Bob
  initialMessage: X3dhInitialMessage; // o que Alice mandou
}

// Wrapper de I/O do lado de Bob: carrega as chaves locais, consome a OPK
// usada e chama o núcleo puro.
export async function receiveInitialMessage(params: ReceiveInitialMessageParams): Promise<X3dhResponderResult> {
  const myKeys = await loadDeviceKeys(params.myDeviceId);
  if (!myKeys) throw new Error('Chaves locais não encontradas - gera as chaves primeiro');

  if (myKeys.signedPrekeyId !== params.initialMessage.signedPrekeyId) {
    throw new Error('A mensagem inicial refere uma signed prekey que já não é a actual');
  }

  const identityKey: KeyPair = {
    privateKey: base64ToBytes(myKeys.identityPrivateKey),
    publicKey: base64ToBytes(myKeys.identityPublicKey),
  };
  const signedPrekeyPrivate = base64ToBytes(myKeys.signedPrekeyPrivateKey);

  let oneTimePrekeyPrivate: Uint8Array | null = null;
  if (params.initialMessage.oneTimePrekeyId !== null) {
    oneTimePrekeyPrivate = await consumeOneTimePrekey(params.myDeviceId, params.initialMessage.oneTimePrekeyId);
    if (!oneTimePrekeyPrivate) {
      throw new Error('One-time prekey referida na mensagem inicial já não existe localmente');
    }
  }

  return deriveResponderSharedKey({ identityKey, signedPrekeyPrivate, oneTimePrekeyPrivate }, params.initialMessage);
}
