import { describe, it, expect, vi, beforeEach } from 'vitest';

import { saveSession, loadSession, deleteSession, type SessionRecord } from './sessionStore';
import { createSessionPair, send, receive } from './testUtils';
import { type RatchetState } from './doubleRatchet';

const memoryStore = new Map<string, string>();

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

beforeEach(() => memoryStore.clear());

function record(state: RatchetState): SessionRecord {
  return { state, pendingInitialMessage: null, initiatorEphemeralKey: null };
}

describe('saveSession / loadSession', () => {
  it('guarda e recupera um estado a meio da conversa, incluindo chaves saltadas', async () => {
    const { alice, bob } = createSessionPair();
    const m1 = send(alice, 'um');
    send(alice, 'dois'); // saltada do lado de Bob
    receive(bob, m1);
    receive(bob, send(alice, 'três'));
    expect(bob.state.skipped.size).toBe(1);

    await saveSession('bob-device', 'alice-device', record(bob.state));
    const loaded = await loadSession('bob-device', 'alice-device');

    expect(loaded).toEqual(record(bob.state));
  });

  it('guarda e recupera o prelúdio pendente de Alice e a EK que criou a sessão de Bob', async () => {
    const { alice } = createSessionPair();
    const full: SessionRecord = {
      state: alice.state,
      pendingInitialMessage: {
        identityKey: new Uint8Array(32).fill(1),
        ephemeralKey: new Uint8Array(32).fill(2),
        signedPrekeyId: 1,
        oneTimePrekeyId: 42,
      },
      initiatorEphemeralKey: new Uint8Array(32).fill(3),
    };

    await saveSession('me', 'other', full);
    expect(await loadSession('me', 'other')).toEqual(full);
  });

  it('a conversa continua correctamente depois de carregar o estado', async () => {
    const { alice, bob } = createSessionPair();
    const delayed = send(alice, 'atrasada');
    receive(bob, send(alice, 'primeira que chega'));

    await saveSession('bob-device', 'alice-device', record(bob.state));
    bob.state = (await loadSession('bob-device', 'alice-device'))!.state;

    expect(receive(bob, delayed)).toBe('atrasada');
    expect(receive(alice, send(bob, 'resposta depois de recarregar'))).toBe(
      'resposta depois de recarregar',
    );
    expect(receive(bob, send(alice, 'e mais uma'))).toBe('e mais uma');
  });

  it('sessões são separadas por par de dispositivos', async () => {
    const { alice } = createSessionPair();
    await saveSession('me', 'device-a', record(alice.state));
    expect(await loadSession('me', 'device-b')).toBeNull();
    expect(await loadSession('device-a', 'me')).toBeNull();
  });

  it('devolve null quando não existe sessão', async () => {
    expect(await loadSession('me', 'ninguem')).toBeNull();
  });

  it('deleteSession apaga a sessão', async () => {
    const { alice } = createSessionPair();
    await saveSession('me', 'other', record(alice.state));
    await deleteSession('me', 'other');
    expect(await loadSession('me', 'other')).toBeNull();
  });
});
