import { describe, it, expect, vi, beforeEach } from 'vitest';

import { saveSession, loadSession, deleteSession } from './sessionStore';
import { createSessionPair, send, receive } from './testUtils';

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

describe('saveSession / loadSession', () => {
  it('guarda e recupera um estado a meio da conversa, incluindo chaves saltadas', async () => {
    const { alice, bob } = createSessionPair();
    const m1 = send(alice, 'um');
    send(alice, 'dois'); // saltada do lado de Bob
    receive(bob, m1);
    receive(bob, send(alice, 'três'));
    expect(bob.state.skipped.size).toBe(1);

    await saveSession('bob-device', 'alice-device', bob.state);
    const loaded = await loadSession('bob-device', 'alice-device');

    expect(loaded).toEqual(bob.state);
  });

  it('a conversa continua correctamente depois de carregar o estado', async () => {
    const { alice, bob } = createSessionPair();
    const delayed = send(alice, 'atrasada');
    receive(bob, send(alice, 'primeira que chega'));

    await saveSession('bob-device', 'alice-device', bob.state);
    bob.state = (await loadSession('bob-device', 'alice-device'))!;

    expect(receive(bob, delayed)).toBe('atrasada');
    expect(receive(alice, send(bob, 'resposta depois de recarregar'))).toBe('resposta depois de recarregar');
    expect(receive(bob, send(alice, 'e mais uma'))).toBe('e mais uma');
  });

  it('sessões são separadas por par de dispositivos', async () => {
    const { alice } = createSessionPair();
    await saveSession('me', 'device-a', alice.state);
    expect(await loadSession('me', 'device-b')).toBeNull();
    expect(await loadSession('device-a', 'me')).toBeNull();
  });

  it('devolve null quando não existe sessão', async () => {
    expect(await loadSession('me', 'ninguem')).toBeNull();
  });

  it('deleteSession apaga a sessão', async () => {
    const { alice } = createSessionPair();
    await saveSession('me', 'other', alice.state);
    await deleteSession('me', 'other');
    expect(await loadSession('me', 'other')).toBeNull();
  });
});
