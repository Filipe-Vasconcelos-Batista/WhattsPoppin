// Double Ratchet - https://signal.org/docs/specifications/doubleratchet/
//
// Segue a spec função a função (RatchetInitAlice/Bob, RatchetEncrypt,
// RatchetDecrypt, TrySkippedMessageKeys, SkipMessageKeys, DHRatchet). Única
// diferença de forma: em vez de mutar o estado, cada operação devolve um
// estado novo - se a decifra falhar, o estado anterior fica intacto, que é
// exactamente o que a spec exige ("discard any changes to the state").

import { concatBytes } from '@noble/hashes/utils.js';

import {
  type KeyPair,
  generateKeyPair,
  dh,
  hkdfRk,
  hmacCk,
  aeadEncrypt,
  aeadDecrypt,
} from './primitives';
import { bytesToBase64 } from './encoding';

// Máximo de chaves de mensagem a saltar numa só cadeia - impede que um
// cabeçalho malicioso com um n gigante obrigue a calcular milhões de chaves.
export const MAX_SKIP = 1000;

const MAX_COUNTER = 0xffffffff;

export interface RatchetHeader {
  dh: Uint8Array; // chave pública ratchet actual de quem envia
  pn: number; // nº de mensagens na cadeia de envio anterior
  n: number; // nº desta mensagem na cadeia de envio actual
}

export interface RatchetState {
  dhs: KeyPair;
  dhr: Uint8Array | null;
  rk: Uint8Array;
  cks: Uint8Array | null;
  ckr: Uint8Array | null;
  ns: number;
  nr: number;
  pn: number;
  skipped: Map<string, Uint8Array>; // MKSKIPPED, chave = `${b64(dh)}:${n}`
  ad: Uint8Array; // AD do X3DH (IK_A || IK_B), fixo durante a sessão
}

export interface EncryptResult {
  state: RatchetState;
  header: RatchetHeader;
  ciphertext: Uint8Array;
}

export interface DecryptResult {
  state: RatchetState;
  plaintext: Uint8Array;
}

function cloneState(state: RatchetState): RatchetState {
  return { ...state, skipped: new Map(state.skipped) };
}

function skippedKey(dhPublicKey: Uint8Array, n: number): string {
  return `${bytesToBase64(dhPublicKey)}:${n}`;
}

function bytesEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}

function assertCounter(value: number, label: string): void {
  if (!Number.isInteger(value) || value < 0 || value > MAX_COUNTER) {
    throw new Error(`${label} inválido no cabeçalho: ${value}`);
  }
}

// dh(32) || pn(4, big-endian) || n(4, big-endian) - tamanho fixo, entra no
// AD do AEAD para que adulterar o cabeçalho faça a decifra falhar.
export function encodeHeader(header: RatchetHeader): Uint8Array {
  const counters = new Uint8Array(8);
  const view = new DataView(counters.buffer);
  view.setUint32(0, header.pn);
  view.setUint32(4, header.n);
  return concatBytes(header.dh, counters);
}

function headerAd(ad: Uint8Array, header: RatchetHeader): Uint8Array {
  return concatBytes(ad, encodeHeader(header));
}

export function initAlice(sk: Uint8Array, bobRatchetPublicKey: Uint8Array, ad: Uint8Array): RatchetState {
  const dhs = generateKeyPair();
  const { rootKey, chainKey } = hkdfRk(sk, dh(dhs.privateKey, bobRatchetPublicKey));
  return {
    dhs,
    dhr: bobRatchetPublicKey,
    rk: rootKey,
    cks: chainKey,
    ckr: null,
    ns: 0,
    nr: 0,
    pn: 0,
    skipped: new Map(),
    ad,
  };
}

// O par ratchet inicial de Bob é a sua signed prekey (a mesma que Alice usou
// no X3DH e recebeu como remoteRatchetKey).
export function initBob(sk: Uint8Array, bobSignedPrekey: KeyPair, ad: Uint8Array): RatchetState {
  return {
    dhs: bobSignedPrekey,
    dhr: null,
    rk: sk,
    cks: null,
    ckr: null,
    ns: 0,
    nr: 0,
    pn: 0,
    skipped: new Map(),
    ad,
  };
}

export function ratchetEncrypt(state: RatchetState, plaintext: Uint8Array): EncryptResult {
  if (!state.cks) {
    throw new Error('Ainda não há cadeia de envio - Bob só pode enviar depois de receber a primeira mensagem');
  }
  const next = cloneState(state);
  const { chainKey, messageKey } = hmacCk(state.cks);
  const header: RatchetHeader = { dh: next.dhs.publicKey, pn: next.pn, n: next.ns };
  next.cks = chainKey;
  next.ns += 1;
  return { state: next, header, ciphertext: aeadEncrypt(messageKey, plaintext, headerAd(next.ad, header)) };
}

export function ratchetDecrypt(
  state: RatchetState,
  header: RatchetHeader,
  ciphertext: Uint8Array,
): DecryptResult {
  assertCounter(header.pn, 'pn');
  assertCounter(header.n, 'n');

  const next = cloneState(state);

  const skipped = trySkippedMessageKeys(next, header, ciphertext);
  if (skipped) return { state: next, plaintext: skipped };

  if (!next.dhr || !bytesEqual(header.dh, next.dhr)) {
    skipMessageKeys(next, header.pn);
    dhRatchet(next, header);
  }
  skipMessageKeys(next, header.n);

  // Depois de dhRatchet ckr existe sempre; sem ele, skipMessageKeys não
  // teria feito nada e aqui não há cadeia de receção.
  if (!next.ckr) throw new Error('Sem cadeia de receção para decifrar esta mensagem');
  const { chainKey, messageKey } = hmacCk(next.ckr);
  next.ckr = chainKey;
  next.nr += 1;

  const plaintext = aeadDecrypt(messageKey, ciphertext, headerAd(next.ad, header));
  return { state: next, plaintext };
}

function trySkippedMessageKeys(
  state: RatchetState,
  header: RatchetHeader,
  ciphertext: Uint8Array,
): Uint8Array | null {
  const key = skippedKey(header.dh, header.n);
  const messageKey = state.skipped.get(key);
  if (!messageKey) return null;
  const plaintext = aeadDecrypt(messageKey, ciphertext, headerAd(state.ad, header));
  state.skipped.delete(key);
  return plaintext;
}

function skipMessageKeys(state: RatchetState, until: number): void {
  if (state.nr + MAX_SKIP < until) {
    throw new Error(`Demasiadas mensagens saltadas (${until - state.nr} > ${MAX_SKIP})`);
  }
  if (!state.ckr || !state.dhr) return;
  while (state.nr < until) {
    const { chainKey, messageKey } = hmacCk(state.ckr);
    state.ckr = chainKey;
    state.skipped.set(skippedKey(state.dhr, state.nr), messageKey);
    state.nr += 1;
  }
}

function dhRatchet(state: RatchetState, header: RatchetHeader): void {
  state.pn = state.ns;
  state.ns = 0;
  state.nr = 0;
  state.dhr = header.dh;

  const receiving = hkdfRk(state.rk, dh(state.dhs.privateKey, state.dhr));
  state.rk = receiving.rootKey;
  state.ckr = receiving.chainKey;

  state.dhs = generateKeyPair();
  const sending = hkdfRk(state.rk, dh(state.dhs.privateKey, state.dhr));
  state.rk = sending.rootKey;
  state.cks = sending.chainKey;
}
