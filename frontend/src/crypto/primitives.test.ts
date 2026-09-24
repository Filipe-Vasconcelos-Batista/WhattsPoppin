// Testa só os primitivos criptográficos em isolamento: acordo DH, KDFs,
// round-trip e adulteração do AEAD, tamanhos de output.
//
// Fora de âmbito nesta camada (fica para X3DH/Double Ratchet em fases
// seguintes): replay, mensagens fora de ordem, transições de estado do
// ratchet, vinculação/autenticação de identity keys, forward secrecy /
// post-compromise security, e resistência a timing attacks (confiança
// herdada das implementações constant-time das @noble/*).

import { describe, it, expect } from 'vitest';
import {
  KEY_LENGTH,
  generateKeyPair,
  dh,
  hkdfRk,
  hmacCk,
  aeadEncrypt,
  aeadDecrypt,
} from './primitives';

describe('generateKeyPair', () => {
  it('produces keys of the correct length', () => {
    const { privateKey, publicKey } = generateKeyPair();
    expect(privateKey.length).toBe(KEY_LENGTH);
    expect(publicKey.length).toBe(KEY_LENGTH);
  });

  it('produces different key pairs on each call', () => {
    const a = generateKeyPair();
    const b = generateKeyPair();
    expect(a.privateKey).not.toEqual(b.privateKey);
    expect(a.publicKey).not.toEqual(b.publicKey);
  });
});

describe('dh', () => {
  it('agrees between both sides', () => {
    const alice = generateKeyPair();
    const bob = generateKeyPair();
    const sharedByAlice = dh(alice.privateKey, bob.publicKey);
    const sharedByBob = dh(bob.privateKey, alice.publicKey);
    expect(sharedByAlice).toEqual(sharedByBob);
  });

  it('returns 32 bytes', () => {
    const alice = generateKeyPair();
    const bob = generateKeyPair();
    expect(dh(alice.privateKey, bob.publicKey).length).toBe(KEY_LENGTH);
  });

  it('rejects keys with the wrong length', () => {
    const { privateKey, publicKey } = generateKeyPair();
    const oversized = new Uint8Array([...publicKey, 0]);
    expect(() => dh(privateKey.slice(0, 31), publicKey)).toThrow();
    expect(() => dh(privateKey, oversized)).toThrow();
  });
});

describe('hkdfRk', () => {
  const rk = new Uint8Array(KEY_LENGTH).fill(1);
  const dhOut = new Uint8Array(KEY_LENGTH).fill(2);

  it('returns a 32-byte root key and chain key', () => {
    const { rootKey, chainKey } = hkdfRk(rk, dhOut);
    expect(rootKey.length).toBe(KEY_LENGTH);
    expect(chainKey.length).toBe(KEY_LENGTH);
  });

  it('is deterministic for the same input', () => {
    const first = hkdfRk(rk, dhOut);
    const second = hkdfRk(rk, dhOut);
    expect(first.rootKey).toEqual(second.rootKey);
    expect(first.chainKey).toEqual(second.chainKey);
  });

  it('rejects inputs with the wrong length', () => {
    expect(() => hkdfRk(rk.slice(0, 31), dhOut)).toThrow();
    expect(() => hkdfRk(rk, dhOut.slice(0, 31))).toThrow();
  });
});

describe('hmacCk', () => {
  const ck = new Uint8Array(KEY_LENGTH).fill(3);

  it('returns a 32-byte chain key and message key', () => {
    const { chainKey, messageKey } = hmacCk(ck);
    expect(chainKey.length).toBe(KEY_LENGTH);
    expect(messageKey.length).toBe(KEY_LENGTH);
  });

  it('is deterministic for the same input', () => {
    const first = hmacCk(ck);
    const second = hmacCk(ck);
    expect(first.chainKey).toEqual(second.chainKey);
    expect(first.messageKey).toEqual(second.messageKey);
  });

  it('rejects a chain key with the wrong length', () => {
    expect(() => hmacCk(ck.slice(0, 31))).toThrow();
  });
});

describe('aeadEncrypt / aeadDecrypt', () => {
  const key = new Uint8Array(KEY_LENGTH).fill(4);
  const ad = new TextEncoder().encode('associated-data');

  const cases: [string, Uint8Array][] = [
    ['empty plaintext', new Uint8Array(0)],
    ['1-byte plaintext', new Uint8Array([42])],
    ['~10KB plaintext', new Uint8Array(10_000).fill(7)],
  ];

  for (const [label, plaintext] of cases) {
    it(`round-trips (${label}, with associated data)`, () => {
      const ciphertext = aeadEncrypt(key, plaintext, ad);
      expect(aeadDecrypt(key, ciphertext, ad)).toEqual(plaintext);
    });

    it(`round-trips (${label}, empty associated data)`, () => {
      const emptyAd = new Uint8Array(0);
      const ciphertext = aeadEncrypt(key, plaintext, emptyAd);
      expect(aeadDecrypt(key, ciphertext, emptyAd)).toEqual(plaintext);
    });
  }

  it('produces output of nonce + plaintext + tag length', () => {
    const plaintext = new Uint8Array(100);
    const ciphertext = aeadEncrypt(key, plaintext, ad);
    expect(ciphertext.length).toBe(12 + plaintext.length + 16);
  });

  it('throws when the ciphertext is tampered with', () => {
    const ciphertext = aeadEncrypt(key, new TextEncoder().encode('hello'), ad);
    const tampered = ciphertext.slice();
    tampered[tampered.length - 1] ^= 0xff;
    expect(() => aeadDecrypt(key, tampered, ad)).toThrow();
  });

  it('throws when the associated data does not match', () => {
    const ciphertext = aeadEncrypt(key, new TextEncoder().encode('hello'), ad);
    const wrongAd = new TextEncoder().encode('wrong-associated-data');
    expect(() => aeadDecrypt(key, ciphertext, wrongAd)).toThrow();
  });

  it('throws when decrypted with the wrong key', () => {
    const ciphertext = aeadEncrypt(key, new TextEncoder().encode('hello'), ad);
    const wrongKey = new Uint8Array(KEY_LENGTH).fill(9);
    expect(() => aeadDecrypt(wrongKey, ciphertext, ad)).toThrow();
  });

  it('rejects a key with the wrong length', () => {
    expect(() =>
      aeadEncrypt(key.slice(0, 31), new Uint8Array(1), ad)
    ).toThrow();
  });
});
