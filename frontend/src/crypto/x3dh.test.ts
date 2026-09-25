// Testa o acordo X3DH: Alice e Bob, cada um do seu lado, têm de chegar à
// mesma SK. Núcleo puro (deriveInitiatorSharedKey/deriveResponderSharedKey)
// sem mocks; wrappers de I/O (initiateSession/receiveInitialMessage) com
// AsyncStorage e ../api/devices mockados, no mesmo padrão de keys.test.ts.

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ed25519 } from '@noble/curves/ed25519.js';
import { generateKeyPair, type KeyPair } from './primitives';
import { generateDeviceKeys, storeDeviceKeys, type OneTimePrekeyMaterial } from './keys';
import { bytesToBase64 } from './encoding';
import {
  deriveInitiatorSharedKey,
  deriveResponderSharedKey,
  SignedPrekeySignatureError,
  initiateSession,
  receiveInitialMessage,
  type X3dhBundle,
  type X3dhResponderLocalKeys,
} from './x3dh';

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
  fetchPrekeyBundle: vi.fn(),
}));

beforeEach(() => {
  memoryStore.clear();
  vi.clearAllMocks();
});

function edKeyPair(): KeyPair {
  const { secretKey, publicKey } = ed25519.keygen();
  return { privateKey: secretKey, publicKey };
}

function bundleFromDevice(
  device: ReturnType<typeof generateDeviceKeys>,
  opk: OneTimePrekeyMaterial | null,
): X3dhBundle {
  return {
    identityKey: device.identityKey.publicKey,
    signedPrekey: device.signedPrekey.publicKey,
    signedPrekeySignature: device.signedPrekeySignature,
    signedPrekeyId: device.signedPrekeyId,
    oneTimePrekey: opk ? opk.keyPair.publicKey : null,
    oneTimePrekeyId: opk ? opk.keyId : null,
  };
}

function localKeysFromDevice(
  device: ReturnType<typeof generateDeviceKeys>,
  opk: OneTimePrekeyMaterial | null,
): X3dhResponderLocalKeys {
  return {
    identityKey: device.identityKey,
    signedPrekeyPrivate: device.signedPrekey.privateKey,
    oneTimePrekeyPrivate: opk ? opk.keyPair.privateKey : null,
  };
}

describe('deriveInitiatorSharedKey / deriveResponderSharedKey', () => {
  it('Alice e Bob chegam à mesma SK (com one-time prekey)', () => {
    const bob = generateDeviceKeys();
    const opk = bob.oneTimePrekeys[0];
    const aliceIdentityKey = edKeyPair();
    const aliceEphemeralKey = generateKeyPair();

    const alice = deriveInitiatorSharedKey(aliceIdentityKey, aliceEphemeralKey, bundleFromDevice(bob, opk));
    const bobSharedKey = deriveResponderSharedKey(localKeysFromDevice(bob, opk), alice.initialMessage);

    expect(bobSharedKey).toEqual(alice.sharedKey);
    expect(alice.sharedKey.length).toBe(32);
  });

  it('Alice e Bob chegam à mesma SK (sem one-time prekey - pool esgotado)', () => {
    const bob = generateDeviceKeys();
    const aliceIdentityKey = edKeyPair();
    const aliceEphemeralKey = generateKeyPair();

    const alice = deriveInitiatorSharedKey(aliceIdentityKey, aliceEphemeralKey, bundleFromDevice(bob, null));
    const bobSharedKey = deriveResponderSharedKey(localKeysFromDevice(bob, null), alice.initialMessage);

    expect(bobSharedKey).toEqual(alice.sharedKey);
  });

  it('a SK com OPK é diferente da SK sem OPK, para o mesmo par de identidades', () => {
    const bob = generateDeviceKeys();
    const opk = bob.oneTimePrekeys[0];
    const aliceIdentityKey = edKeyPair();

    const withOpk = deriveInitiatorSharedKey(aliceIdentityKey, generateKeyPair(), bundleFromDevice(bob, opk));
    const withoutOpk = deriveInitiatorSharedKey(aliceIdentityKey, generateKeyPair(), bundleFromDevice(bob, null));

    expect(withOpk.sharedKey).not.toEqual(withoutOpk.sharedKey);
  });

  it('rejeita um bundle com assinatura inválida', () => {
    const bob = generateDeviceKeys();
    const tamperedSignature = bob.signedPrekeySignature.slice();
    tamperedSignature[0] ^= 0xff;

    const bundle: X3dhBundle = {
      ...bundleFromDevice(bob, bob.oneTimePrekeys[0]),
      signedPrekeySignature: tamperedSignature,
    };

    expect(() => deriveInitiatorSharedKey(edKeyPair(), generateKeyPair(), bundle)).toThrow(
      SignedPrekeySignatureError,
    );
  });

  it('Bob rejeita quando a mensagem refere uma OPK que ele já não tem', () => {
    const bob = generateDeviceKeys();
    const opk = bob.oneTimePrekeys[0];

    const alice = deriveInitiatorSharedKey(edKeyPair(), generateKeyPair(), bundleFromDevice(bob, opk));

    expect(() => deriveResponderSharedKey(localKeysFromDevice(bob, null), alice.initialMessage)).toThrow();
  });

  it('duas sessões diferentes para o mesmo bundle dão SKs diferentes', () => {
    const bob = generateDeviceKeys();
    const opk = bob.oneTimePrekeys[0];
    const aliceIdentityKey = edKeyPair();

    const first = deriveInitiatorSharedKey(aliceIdentityKey, generateKeyPair(), bundleFromDevice(bob, opk));
    const second = deriveInitiatorSharedKey(aliceIdentityKey, generateKeyPair(), bundleFromDevice(bob, opk));

    expect(first.sharedKey).not.toEqual(second.sharedKey);
  });
});

describe('initiateSession / receiveInitialMessage', () => {
  it('Alice e Bob chegam à mesma SK através dos wrappers de I/O', async () => {
    const { fetchPrekeyBundle } = await import('../api/devices');

    const aliceDeviceId = 'alice-device';
    const bobDeviceId = 'bob-device';
    const bobKeys = generateDeviceKeys();
    const bobOpk = bobKeys.oneTimePrekeys[0];

    await storeDeviceKeys(aliceDeviceId, generateDeviceKeys());
    await storeDeviceKeys(bobDeviceId, bobKeys);

    vi.mocked(fetchPrekeyBundle).mockResolvedValue({
      identity_key: bytesToBase64(bobKeys.identityKey.publicKey),
      signed_prekey: bytesToBase64(bobKeys.signedPrekey.publicKey),
      signed_prekey_signature: bytesToBase64(bobKeys.signedPrekeySignature),
      signed_prekey_id: bobKeys.signedPrekeyId,
      one_time_prekey_id: bobOpk.keyId,
      one_time_prekey: bytesToBase64(bobOpk.keyPair.publicKey),
    });

    const aliceResult = await initiateSession({ myDeviceId: aliceDeviceId, recipientDeviceId: bobDeviceId });
    const bobSharedKey = await receiveInitialMessage({
      myDeviceId: bobDeviceId,
      initialMessage: aliceResult.initialMessage,
    });

    expect(bobSharedKey).toEqual(aliceResult.sharedKey);
  });

  it('a OPK usada deixa de estar disponível localmente para Bob depois de consumida', async () => {
    const { fetchPrekeyBundle } = await import('../api/devices');

    const aliceDeviceId = 'alice-device-2';
    const bobDeviceId = 'bob-device-2';
    const bobKeys = generateDeviceKeys();
    const bobOpk = bobKeys.oneTimePrekeys[0];

    await storeDeviceKeys(aliceDeviceId, generateDeviceKeys());
    await storeDeviceKeys(bobDeviceId, bobKeys);

    vi.mocked(fetchPrekeyBundle).mockResolvedValue({
      identity_key: bytesToBase64(bobKeys.identityKey.publicKey),
      signed_prekey: bytesToBase64(bobKeys.signedPrekey.publicKey),
      signed_prekey_signature: bytesToBase64(bobKeys.signedPrekeySignature),
      signed_prekey_id: bobKeys.signedPrekeyId,
      one_time_prekey_id: bobOpk.keyId,
      one_time_prekey: bytesToBase64(bobOpk.keyPair.publicKey),
    });

    const aliceResult = await initiateSession({ myDeviceId: aliceDeviceId, recipientDeviceId: bobDeviceId });
    await receiveInitialMessage({ myDeviceId: bobDeviceId, initialMessage: aliceResult.initialMessage });

    await expect(
      receiveInitialMessage({ myDeviceId: bobDeviceId, initialMessage: aliceResult.initialMessage }),
    ).rejects.toThrow();
  });
});
