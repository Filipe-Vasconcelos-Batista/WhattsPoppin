// Uint8Array <-> base64 sem depender de Buffer/atob/btoa (indisponíveis no
// Hermes/React Native). RFC 4648 standard alphabet, com padding.

const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

export function bytesToBase64(bytes: Uint8Array): string {
  let result = '';
  for (let i = 0; i < bytes.length; i += 3) {
    const b0 = bytes[i];
    const b1 = bytes[i + 1];
    const b2 = bytes[i + 2];
    const hasB1 = i + 1 < bytes.length;
    const hasB2 = i + 2 < bytes.length;

    result += CHARS[b0 >> 2];
    result += CHARS[((b0 & 0x03) << 4) | (hasB1 ? b1 >> 4 : 0)];
    result += hasB1 ? CHARS[((b1 & 0x0f) << 2) | (hasB2 ? b2 >> 6 : 0)] : '=';
    result += hasB2 ? CHARS[b2 & 0x3f] : '=';
  }
  return result;
}

export function base64ToBytes(base64: string): Uint8Array {
  const clean = base64.replace(/=+$/, '');
  const bytes: number[] = [];
  let buffer = 0;
  let bits = 0;

  for (const char of clean) {
    const value = CHARS.indexOf(char);
    if (value === -1) throw new Error(`Invalid base64 character: ${char}`);
    buffer = (buffer << 6) | value;
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      bytes.push((buffer >> bits) & 0xff);
    }
  }
  return new Uint8Array(bytes);
}
