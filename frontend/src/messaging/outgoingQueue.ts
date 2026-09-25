// Outbox de quem envia: cada mensagem fica guardada localmente até o
// servidor confirmar ("sent") que a pôs na fila dele. Se o socket estiver em
// baixo, espera; quando abre, sai tudo por ordem.
//
// Cifra-se uma só vez: os envelopes ficam guardados no item e um reenvio
// manda exactamente os mesmos bytes, para o Double Ratchet não avançar duas
// vezes por causa da mesma mensagem.

import AsyncStorage from '@react-native-async-storage/async-storage';

import type { WireEnvelope } from '../crypto/messaging';

export interface OutgoingItem {
  clientMessageId: string;
  conversationId: string;
  text: string;
  envelopes: WireEnvelope[] | null;
}

export interface OutgoingQueueDeps {
  storageKey: string;
  encrypt: (conversationId: string, text: string) => Promise<WireEnvelope[]>;
  // Devolve false se o socket não estiver aberto (nada foi enviado).
  send: (payload: Record<string, unknown>) => boolean;
}

export interface OutgoingQueue {
  enqueue: (item: Omit<OutgoingItem, 'envelopes'>) => Promise<void>;
  flush: () => Promise<void>;
  onSocketOpen: () => Promise<void>;
  confirmSent: (clientMessageId: string) => Promise<void>;
}

export function createOutgoingQueue(deps: OutgoingQueueDeps): OutgoingQueue {
  // Enviadas nesta ligação e ainda sem "sent" - não se reenviam até o
  // socket voltar a abrir (aí sim, o "sent" pode ter-se perdido).
  let sentThisConnection = new Set<string>();
  let chain: Promise<void> = Promise.resolve();

  function serially(task: () => Promise<void>): Promise<void> {
    const result = chain.then(task);
    chain = result.catch(() => undefined);
    return result;
  }

  async function load(): Promise<OutgoingItem[]> {
    const raw = await AsyncStorage.getItem(deps.storageKey);
    if (!raw) return [];
    try {
      return JSON.parse(raw) as OutgoingItem[];
    } catch {
      return [];
    }
  }

  async function save(items: OutgoingItem[]): Promise<void> {
    await AsyncStorage.setItem(deps.storageKey, JSON.stringify(items));
  }

  function flush(): Promise<void> {
    return serially(async () => {
      const items = await load();
      for (const item of items) {
        if (sentThisConnection.has(item.clientMessageId)) continue;

        if (!item.envelopes) {
          let envelopes: WireEnvelope[];
          try {
            envelopes = await deps.encrypt(item.conversationId, item.text);
          } catch (error) {
            // Ex.: sem rede para ir buscar os devices/bundles - pára aqui para
            // não trocar a ordem, e tenta de novo no próximo flush.
            console.warn('Falha ao cifrar mensagem da outbox:', error);
            return;
          }
          // Destinatário sem devices com chaves: fica pendente, não bloqueia
          // as mensagens seguintes.
          if (envelopes.length === 0) continue;
          item.envelopes = envelopes;
          await save(items);
        }

        const sent = deps.send({
          conversation_id: item.conversationId,
          client_message_id: item.clientMessageId,
          envelopes: item.envelopes,
        });
        if (!sent) return;
        sentThisConnection.add(item.clientMessageId);
      }
    });
  }

  function enqueue(item: Omit<OutgoingItem, 'envelopes'>): Promise<void> {
    return serially(async () => {
      const items = await load();
      items.push({ ...item, envelopes: null });
      await save(items);
    }).then(flush);
  }

  function onSocketOpen(): Promise<void> {
    sentThisConnection = new Set();
    return flush();
  }

  function confirmSent(clientMessageId: string): Promise<void> {
    return serially(async () => {
      const items = await load();
      await save(items.filter((item) => item.clientMessageId !== clientMessageId));
      sentThisConnection.delete(clientMessageId);
    });
  }

  return { enqueue, flush, onSocketOpen, confirmSent };
}
