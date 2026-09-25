import { describe, it, expect } from 'vitest';
import { utf8ToBytes } from '@noble/hashes/utils.js';
import { bytesToBase64, base64ToBytes } from './encoding';

describe('bytesToBase64 / base64ToBytes', () => {
  it('matches a known vector', () => {
    expect(bytesToBase64(utf8ToBytes('foobar'))).toBe('Zm9vYmFy');
  });

  it('round-trips across all padding cases (0..33 bytes)', () => {
    for (let length = 0; length <= 33; length++) {
      const bytes = new Uint8Array(length).map((_, i) => (i * 7 + 1) % 256);
      expect(base64ToBytes(bytesToBase64(bytes))).toEqual(bytes);
    }
  });

  it('rejects an invalid character', () => {
    expect(() => base64ToBytes('not-valid-base64!')).toThrow();
  });
});
