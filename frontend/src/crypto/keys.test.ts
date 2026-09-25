import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ed25519 } from '@noble/curves/ed25519.js';
import {
  generateDeviceKeys,
  storeDeviceKeys,
  loadDeviceKeys,
  ONE_TIME_PREKEY_BATCH_SIZE,
} from './keys';

const memoryStore = new Map<string, string>();

vi.mock('@react-native-async-storage/async-storage', () => ({
  default: {
    getItem: vi.fn(async (key: string) => memoryStore.get(key) ?? null),
    setItem: vi.fn(async (key: string, value: string) => {
      memoryStore.set(key, value);
    }),
  },
}));

vi.mock('../api/devices', () => ({
  publishDeviceKeys: vi.fn(async () => {}),
}));

beforeEach(() => memoryStore.clear());

describe('generateDeviceKeys', () => {
  it('produces keys of the correct length', () => {
    const keys = generateDeviceKeys();
    expect(keys.identityKey.privateKey.length).toBe(32);
    expect(keys.identityKey.publicKey.length).toBe(32);
    expect(keys.signedPrekey.privateKey.length).toBe(32);
    expect(keys.signedPrekey.publicKey.length).toBe(32);
    expect(keys.signedPrekeySignature.length).toBe(64);
  });

  it('generates a full batch of one-time prekeys with unique key ids', () => {
    const keys = generateDeviceKeys();
    expect(keys.oneTimePrekeys.length).toBe(ONE_TIME_PREKEY_BATCH_SIZE);
    const keyIds = keys.oneTimePrekeys.map((opk) => opk.keyId);
    expect(new Set(keyIds).size).toBe(keyIds.length);
  });

  it('produces different keys on each call', () => {
    const a = generateDeviceKeys();
    const b = generateDeviceKeys();
    expect(a.identityKey.privateKey).not.toEqual(b.identityKey.privateKey);
  });

  it('signs the signed prekey with the identity key', () => {
    const keys = generateDeviceKeys();
    const valid = ed25519.verify(
      keys.signedPrekeySignature,
      keys.signedPrekey.publicKey,
      keys.identityKey.publicKey,
    );
    expect(valid).toBe(true);
  });
});

describe('storeDeviceKeys / loadDeviceKeys', () => {
  it('round-trips key material through AsyncStorage', async () => {
    const deviceId = 'device-123';
    const keys = generateDeviceKeys();
    await storeDeviceKeys(deviceId, keys);
    const loaded = await loadDeviceKeys(deviceId);
    expect(loaded).not.toBeNull();
    expect(loaded!.oneTimePrekeys.length).toBe(keys.oneTimePrekeys.length);
  });

  it('returns null when nothing is stored', async () => {
    expect(await loadDeviceKeys('unknown-device')).toBeNull();
  });

  it('merges one-time prekeys across calls instead of overwriting them', async () => {
    const deviceId = 'device-456';
    const first = generateDeviceKeys();
    await storeDeviceKeys(deviceId, first);

    const second = generateDeviceKeys();
    await storeDeviceKeys(deviceId, second);

    const loaded = await loadDeviceKeys(deviceId);
    expect(loaded!.oneTimePrekeys.length).toBe(
      first.oneTimePrekeys.length + second.oneTimePrekeys.length,
    );
  });
});
