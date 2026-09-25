import { describe, it, expect, vi, beforeEach } from 'vitest';

import type { WireEnvelope } from '../crypto/messaging';
import { createOutgoingQueue, type OutgoingItem } from './outgoingQueue';

const memoryStore = new Map<string, string>();

vi.mock('@react-native-async-storage/async-storage', () => ({
  default: {
    getItem: vi.fn(async (key: string) => memoryStore.get(key) ?? null),
    setItem: vi.fn(async (key: string, value: string) => {
      memoryStore.set(key, value);
    }),
  },
}));

const STORAGE_KEY = 'test.outbox';

function envelopeFor(text: string): WireEnvelope {
  return {
    device_id: 'bob-device',
    header: { dh: 'ZGg=', pn: 0, n: 0 },
    ciphertext: `cifrado:${text}`,
    x3dh: null,
  };
}

function setup(options: { socketOpen?: boolean } = {}) {
  const state = { socketOpen: options.socketOpen ?? true };
  const sent: Record<string, unknown>[] = [];
  const encrypt = vi.fn(async (_conversationId: string, text: string) => [envelopeFor(text)]);
  const send = vi.fn((payload: Record<string, unknown>) => {
    if (!state.socketOpen) return false;
    sent.push(payload);
    return true;
  });
  const queue = createOutgoingQueue({ storageKey: STORAGE_KEY, encrypt, send });
  return { queue, encrypt, send, sent, state };
}

function stored(): OutgoingItem[] {
  return JSON.parse(memoryStore.get(STORAGE_KEY) ?? '[]') as OutgoingItem[];
}

function item(n: number) {
  return { clientMessageId: `id-${n}`, conversationId: 'conv-1', text: `mensagem ${n}` };
}

beforeEach(() => memoryStore.clear());

describe('createOutgoingQueue', () => {
  it('envia por ordem com o client_message_id e fica guardada até ao "sent"', async () => {
    const { queue, sent } = setup();
    await queue.enqueue(item(1));
    await queue.enqueue(item(2));

    expect(sent.map((payload) => payload.client_message_id)).toEqual(['id-1', 'id-2']);
    expect(sent[0]).toMatchObject({
      conversation_id: 'conv-1',
      envelopes: [envelopeFor('mensagem 1')],
    });
    expect(stored().map((i) => i.clientMessageId)).toEqual(['id-1', 'id-2']);

    await queue.confirmSent('id-1');
    expect(stored().map((i) => i.clientMessageId)).toEqual(['id-2']);
  });

  it('com o socket fechado fica pendente e sai quando o socket abre', async () => {
    const { queue, sent, state } = setup({ socketOpen: false });
    await queue.enqueue(item(1));
    await queue.enqueue(item(2));
    expect(sent).toEqual([]);

    state.socketOpen = true;
    await queue.onSocketOpen();
    expect(sent.map((payload) => payload.client_message_id)).toEqual(['id-1', 'id-2']);
  });

  it('cifra uma só vez: um reenvio manda os mesmos envelopes', async () => {
    const { queue, sent, encrypt } = setup();
    await queue.enqueue(item(1));
    await queue.onSocketOpen(); // religou sem ter chegado o "sent"

    expect(encrypt).toHaveBeenCalledTimes(1);
    expect(sent).toHaveLength(2);
    expect(sent[1].envelopes).toEqual(sent[0].envelopes);
  });

  it('não reenvia na mesma ligação o que já enviou', async () => {
    const { queue, sent } = setup();
    await queue.enqueue(item(1));
    await queue.flush();
    await queue.enqueue(item(2));

    expect(sent.map((payload) => payload.client_message_id)).toEqual(['id-1', 'id-2']);
  });

  it('se a cifra falhar pára, mantém a ordem e retoma depois', async () => {
    const { queue, sent, encrypt } = setup();
    encrypt.mockRejectedValueOnce(new Error('sem rede'));
    await queue.enqueue(item(1));
    await queue.enqueue(item(2));

    expect(sent.map((payload) => payload.client_message_id)).toEqual(['id-1', 'id-2']);
    expect(encrypt).toHaveBeenCalledTimes(3);
  });

  it('destinatário sem devices com chaves fica pendente sem bloquear as seguintes', async () => {
    const { queue, sent, encrypt } = setup();
    encrypt.mockImplementation(async (conversationId: string, text: string) =>
      conversationId === 'conv-sem-devices' ? [] : [envelopeFor(text)],
    );
    await queue.enqueue({ ...item(1), conversationId: 'conv-sem-devices' });
    await queue.enqueue(item(2));

    expect(sent.map((payload) => payload.client_message_id)).toEqual(['id-2']);
    expect(stored().find((i) => i.clientMessageId === 'id-1')?.envelopes).toBeNull();
  });

  it('sobrevive a recarregar a app (está persistida, já cifrada)', async () => {
    const first = setup({ socketOpen: false });
    await first.queue.enqueue(item(1));
    expect(first.encrypt).toHaveBeenCalledTimes(1);

    const afterReload = setup();
    await afterReload.queue.onSocketOpen();

    expect(afterReload.sent.map((payload) => payload.client_message_id)).toEqual(['id-1']);
    expect(afterReload.sent[0].envelopes).toEqual([envelopeFor('mensagem 1')]);
    expect(afterReload.encrypt).not.toHaveBeenCalled();
  });
});
