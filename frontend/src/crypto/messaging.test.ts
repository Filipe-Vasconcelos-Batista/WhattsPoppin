// Testa a orquestração completa entre dispositivos simulados: abrir sessão
// pelo prelúdio X3DH, repeti-lo até haver resposta, mensagens perdidas,
// adulteradas, e decifras em paralelo pela fila. O "servidor" (bundles e
// lista de devices) é mockado, o resto é real.

import { describe, it, expect, vi, beforeEach } from 'vitest';

import { fetchPrekeyBundle } from '../api/devices';
import { fetchRecipientDevices } from '../api/conversations';
import { bytesToBase64 } from './encoding';
import {
  ONE_TIME_PREKEY_BATCH_SIZE,
  generateDeviceKeys,
  loadDeviceKeys,
  storeDeviceKeys,
  type DeviceKeyMaterial,
  type OneTimePrekeyMaterial,
} from './keys';
import {
  decryptFromDevice,
  decryptIncoming,
  encryptForConversation,
  encryptForDevice,
  type IncomingEncryptedMessage,
  type WireEnvelope,
} from './messaging';
import { loadSession } from './sessionStore';

const memoryStore = new Map<string, string>();
const published = new Map<string, { keys: DeviceKeyMaterial; opks: OneTimePrekeyMaterial[] }>();

vi.mock('@react-native-async-storage/async-storage', () => ({
  default: {
    getItem: vi.fn(async (key: string) => memoryStore.get(key) ?? null),
    setItem: vi.fn(async (key: string, value: string) => {
      memoryStore.set(key, value);
    }),
    removeItem: vi.fn(async (key: string) => {
      memoryStore.delete(key);
    }),
  },
}));

vi.mock('../api/devices', () => ({
  publishDeviceKeys: vi.fn(async () => {}),
  fetchPrekeyBundle: vi.fn(),
}));

vi.mock('../api/conversations', () => ({
  fetchRecipientDevices: vi.fn(),
}));

const ALICE = 'alice-device';
const BOB = 'bob-device';

beforeEach(async () => {
  memoryStore.clear();
  published.clear();
  vi.clearAllMocks();

  // Mesmo comportamento do backend: cada bundle entrega (e gasta) uma OPK
  vi.mocked(fetchPrekeyBundle).mockImplementation(async (deviceId: string) => {
    const entry = published.get(deviceId);
    if (!entry) throw new Error('Device não encontrado');
    const opk = entry.opks.shift() ?? null;
    return {
      identity_key: bytesToBase64(entry.keys.identityKey.publicKey),
      signed_prekey: bytesToBase64(entry.keys.signedPrekey.publicKey),
      signed_prekey_signature: bytesToBase64(entry.keys.signedPrekeySignature),
      signed_prekey_id: entry.keys.signedPrekeyId,
      one_time_prekey_id: opk ? opk.keyId : null,
      one_time_prekey: opk ? bytesToBase64(opk.keyPair.publicKey) : null,
    };
  });

  await setupDevice(ALICE);
  await setupDevice(BOB);
});

async function setupDevice(deviceId: string): Promise<void> {
  const keys = generateDeviceKeys();
  await storeDeviceKeys(deviceId, keys);
  published.set(deviceId, { keys, opks: [...keys.oneTimePrekeys] });
}

function incoming(envelope: WireEnvelope): IncomingEncryptedMessage {
  return { header: envelope.header, ciphertext: envelope.ciphertext, x3dh: envelope.x3dh };
}

async function localOpkCount(deviceId: string): Promise<number> {
  return (await loadDeviceKeys(deviceId))!.oneTimePrekeys.length;
}

describe('encryptForDevice / decryptFromDevice', () => {
  it('a primeira mensagem leva o prelúdio X3DH e o destinatário decifra', async () => {
    const envelope = await encryptForDevice(ALICE, BOB, 'olá bob');

    expect(envelope.device_id).toBe(BOB);
    expect(envelope.x3dh).not.toBeNull();
    expect(envelope.ciphertext).not.toContain('olá');
    expect(await decryptFromDevice(BOB, ALICE, incoming(envelope))).toBe('olá bob');
  });

  it('o prelúdio repete-se até haver resposta, sem gastar outra OPK, e depois desaparece', async () => {
    const first = await encryptForDevice(ALICE, BOB, 'um');
    const second = await encryptForDevice(ALICE, BOB, 'dois');
    expect(second.x3dh).toEqual(first.x3dh);

    expect(await decryptFromDevice(BOB, ALICE, incoming(first))).toBe('um');
    expect(await decryptFromDevice(BOB, ALICE, incoming(second))).toBe('dois');
    expect(await localOpkCount(BOB)).toBe(ONE_TIME_PREKEY_BATCH_SIZE - 1);

    const reply = await encryptForDevice(BOB, ALICE, 'resposta');
    expect(reply.x3dh).toBeNull();
    expect(await decryptFromDevice(ALICE, BOB, incoming(reply))).toBe('resposta');

    const afterReply = await encryptForDevice(ALICE, BOB, 'três');
    expect(afterReply.x3dh).toBeNull();
    expect(await decryptFromDevice(BOB, ALICE, incoming(afterReply))).toBe('três');
  });

  it('se a primeira mensagem se perder, a segunda abre a sessão e a primeira ainda decifra depois', async () => {
    const lost = await encryptForDevice(ALICE, BOB, 'perdida');
    const second = await encryptForDevice(ALICE, BOB, 'segunda');

    expect(await decryptFromDevice(BOB, ALICE, incoming(second))).toBe('segunda');
    expect(await decryptFromDevice(BOB, ALICE, incoming(lost))).toBe('perdida');
  });

  it('uma mensagem adulterada não gasta a OPK nem grava sessão, e a original decifra depois', async () => {
    const envelope = await encryptForDevice(ALICE, BOB, 'intacta');
    const tampered: WireEnvelope = {
      ...envelope,
      ciphertext: envelope.ciphertext.startsWith('A')
        ? `B${envelope.ciphertext.slice(1)}`
        : `A${envelope.ciphertext.slice(1)}`,
    };

    await expect(decryptFromDevice(BOB, ALICE, incoming(tampered))).rejects.toThrow();
    expect(await localOpkCount(BOB)).toBe(ONE_TIME_PREKEY_BATCH_SIZE);
    expect(await loadSession(BOB, ALICE)).toBeNull();

    expect(await decryptFromDevice(BOB, ALICE, incoming(envelope))).toBe('intacta');
  });

  it('rejeita uma mensagem sem sessão e sem prelúdio', async () => {
    const envelope = await encryptForDevice(ALICE, BOB, 'x');
    await expect(
      decryptFromDevice(BOB, ALICE, { ...incoming(envelope), x3dh: null }),
    ).rejects.toThrow(/prelúdio/);
  });
});

describe('encryptForConversation / decryptIncoming', () => {
  it('cifra um envelope por dispositivo e ignora os que falham', async () => {
    await setupDevice('bob-phone');
    vi.mocked(fetchRecipientDevices).mockResolvedValue([BOB, 'bob-phone', 'device-sem-bundle']);

    const envelopes = await encryptForConversation(ALICE, 'conversation-1', 'para todos');

    expect(envelopes.map((e) => e.device_id)).toEqual([BOB, 'bob-phone']);
    expect(await decryptIncoming(BOB, ALICE, incoming(envelopes[0]))).toBe('para todos');
    expect(await decryptIncoming('bob-phone', ALICE, incoming(envelopes[1]))).toBe('para todos');
  });

  it('decifras disparadas em paralelo saem todas certas e a sessão fica consistente', async () => {
    const envelopes: WireEnvelope[] = [];
    for (let i = 0; i < 5; i++) envelopes.push(await encryptForDevice(ALICE, BOB, `mensagem ${i}`));

    const texts = await Promise.all(envelopes.map((e) => decryptIncoming(BOB, ALICE, incoming(e))));

    expect(texts).toEqual([0, 1, 2, 3, 4].map((i) => `mensagem ${i}`));
    expect(await localOpkCount(BOB)).toBe(ONE_TIME_PREKEY_BATCH_SIZE - 1);
    const reply = await encryptForDevice(BOB, ALICE, 'recebi tudo');
    expect(await decryptIncoming(ALICE, BOB, incoming(reply))).toBe('recebi tudo');
  });
});
