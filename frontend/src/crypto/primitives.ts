import { x25519, ed25519 } from '@noble/curves/ed25519.js';
import { hkdf } from '@noble/hashes/hkdf.js';
import { hmac } from '@noble/hashes/hmac.js';
import { sha256 } from '@noble/hashes/sha2.js';
import { randomBytes, concatBytes, utf8ToBytes } from '@noble/hashes/utils.js';
import { chacha20poly1305 } from '@noble/ciphers/chacha.js';

export const KEY_LENGTH = 32;
const NONCE_LENGTH = 12;
const TAG_LENGTH = 16;

function assertLength(bytes: Uint8Array, length: number, label: string): void {
  if (bytes.length !== length) {
    throw new Error(`${label} must be ${length} bytes, got ${bytes.length}`);
  }
}

export interface KeyPair {
  privateKey: Uint8Array;
  publicKey: Uint8Array;
}

export function generateKeyPair(): KeyPair {
  const { secretKey, publicKey } = x25519.keygen();
  return { privateKey: secretKey, publicKey };
}

export function dh(privateKey: Uint8Array, publicKey: Uint8Array): Uint8Array {
  assertLength(privateKey, KEY_LENGTH, 'privateKey');
  assertLength(publicKey, KEY_LENGTH, 'publicKey');
  return x25519.getSharedSecret(privateKey, publicKey);
}

// Conversão Edwards -> Montgomery (Ed25519 -> X25519). A identity key deste
// app é Ed25519 (reutilizada para assinar a signed prekey), mas o X3DH
// precisa de X25519 para fazer DH - este é o mapa birracional padrão que
// permite usar a mesma chave para as duas coisas.
export function edPublicKeyToX25519(edPublicKey: Uint8Array): Uint8Array {
  assertLength(edPublicKey, KEY_LENGTH, 'edPublicKey');
  return ed25519.utils.toMontgomery(edPublicKey);
}

export function edPrivateKeyToX25519(edPrivateKey: Uint8Array): Uint8Array {
  assertLength(edPrivateKey, KEY_LENGTH, 'edPrivateKey');
  return ed25519.utils.toMontgomerySecret(edPrivateKey);
}

export interface RootKeyUpdate {
  rootKey: Uint8Array;
  chainKey: Uint8Array;
}

// Label de domain-separation para KDF_RK. Livre de renomear, mas tem de ficar
// estável entre versões da app assim que ratchets reais dependam dela.
const HKDF_RK_INFO = utf8ToBytes('WhattsPoppin-DoubleRatchet-RK-v1');

export function hkdfRk(rk: Uint8Array, dhOut: Uint8Array): RootKeyUpdate {
  assertLength(rk, KEY_LENGTH, 'rk');
  assertLength(dhOut, KEY_LENGTH, 'dhOut');
  const okm = hkdf(sha256, dhOut, rk, HKDF_RK_INFO, 64);
  return { rootKey: okm.slice(0, 32), chainKey: okm.slice(32, 64) };
}

export interface ChainKeyUpdate {
  chainKey: Uint8Array;
  messageKey: Uint8Array;
}

// Constantes do exemplo de KDF_CK no próprio spec do Double Ratchet
// (inputs de um único byte: 0x01 -> message key, 0x02 -> next chain key).
const CK_MESSAGE_KEY_INPUT = new Uint8Array([0x01]);
const CK_NEXT_CHAIN_KEY_INPUT = new Uint8Array([0x02]);

export function hmacCk(ck: Uint8Array): ChainKeyUpdate {
  assertLength(ck, KEY_LENGTH, 'ck');
  return {
    messageKey: hmac(sha256, ck, CK_MESSAGE_KEY_INPUT),
    chainKey: hmac(sha256, ck, CK_NEXT_CHAIN_KEY_INPUT),
  };
}

const KDF_X3DH_INFO = utf8ToBytes('WhattsPoppin-X3DH-SK-v1');
const KDF_X3DH_SALT = new Uint8Array(KEY_LENGTH);

export function kdfX3dh(ikm: Uint8Array): Uint8Array {
  return hkdf(sha256, ikm, KDF_X3DH_SALT, KDF_X3DH_INFO, KEY_LENGTH);
}

// Formato do output: nonce(12) || ciphertext+tag(plaintext.length + 16)
export function aeadEncrypt(
  key: Uint8Array,
  plaintext: Uint8Array,
  associatedData: Uint8Array,
): Uint8Array {
  assertLength(key, KEY_LENGTH, 'key');
  const nonce = randomBytes(NONCE_LENGTH);
  const sealed = chacha20poly1305(key, nonce, associatedData).encrypt(plaintext);
  return concatBytes(nonce, sealed);
}

export function aeadDecrypt(
  key: Uint8Array,
  ciphertext: Uint8Array,
  associatedData: Uint8Array,
): Uint8Array {
  assertLength(key, KEY_LENGTH, 'key');
  if (ciphertext.length < NONCE_LENGTH + TAG_LENGTH) {
    throw new Error('ciphertext too short to contain nonce and auth tag');
  }
  const nonce = ciphertext.subarray(0, NONCE_LENGTH);
  const sealed = ciphertext.subarray(NONCE_LENGTH);
  return chacha20poly1305(key, nonce, associatedData).decrypt(sealed);
}
