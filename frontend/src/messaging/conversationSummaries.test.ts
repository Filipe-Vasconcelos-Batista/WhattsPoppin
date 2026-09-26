import { describe, it, expect } from 'vitest';

import { buildConversationSummaries, initialsFor, totalUnread } from './conversationSummaries';
import type { ChatMessage } from '../types/chat';

const NOW = new Date(2026, 8, 24, 15, 0);
const ANA = { user_id: 'ana', display_name: 'Ana Silva' };
const RUI = { user_id: 'rui', display_name: 'Rui' };
const EVA = { user_id: 'eva', display_name: 'Eva' };
const CONVERSATION_USERS = { 'c-ana': 'ana', 'c-rui': 'rui' };

function text(
  conversationId: string,
  authorId: string,
  body: string,
  extra: Partial<Extract<ChatMessage, { kind: 'text' }>> = {},
): ChatMessage {
  return {
    id: `${conversationId}-${body}`,
    conversationId,
    kind: 'text',
    authorId,
    text: body,
    timeLabel: '10:00',
    ...extra,
  };
}

describe('buildConversationSummaries', () => {
  it('sem mensagens, mantém a ordem do servidor e o convite para conversar', () => {
    const summaries = buildConversationSummaries([ANA, RUI], [], CONVERSATION_USERS, { now: NOW });

    expect(summaries.map((summary) => summary.id)).toEqual(['ana', 'rui']);
    expect(summaries[0]).toMatchObject({
      title: 'Ana Silva',
      initials: 'AS',
      lastMessagePreview: 'Toca para conversar',
      timeLabel: '',
      unreadCount: undefined,
    });
  });

  it('mostra a última mensagem, com "Tu:" quando é minha', () => {
    const messages = [text('c-ana', 'them', 'olá'), text('c-ana', 'me', 'tudo bem?')];

    const [ana] = buildConversationSummaries([ANA], messages, CONVERSATION_USERS, { now: NOW });

    expect(ana.lastMessagePreview).toBe('Tu: tudo bem?');
  });

  it('a conversa com a mensagem mais recente vai para o topo; sem conversa fica no fim', () => {
    const messages = [text('c-ana', 'them', 'primeiro'), text('c-rui', 'them', 'depois')];

    const summaries = buildConversationSummaries([EVA, ANA, RUI], messages, CONVERSATION_USERS, {
      now: NOW,
    });

    expect(summaries.map((summary) => summary.id)).toEqual(['rui', 'ana', 'eva']);
  });

  it('conta só as recebidas por ver', () => {
    const messages = [
      text('c-ana', 'them', 'vista', { seen: true }),
      text('c-ana', 'them', 'recibo já saiu', { readReceiptSent: true }),
      text('c-ana', 'me', 'minha'),
      text('c-ana', 'them', 'nova 1'),
      text('c-ana', 'them', 'nova 2'),
    ];

    const summaries = buildConversationSummaries([ANA], messages, CONVERSATION_USERS, { now: NOW });

    expect(summaries[0].unreadCount).toBe(2);
    expect(totalUnread(summaries)).toBe(2);
  });

  it('usa sentAt para a hora quando existe, senão o timeLabel guardado', () => {
    const withSentAt = [
      text('c-ana', 'them', 'ontem', { sentAt: new Date(2026, 8, 23, 20, 0).getTime() }),
    ];
    const withoutSentAt = [text('c-rui', 'them', 'antiga')];

    const [ana] = buildConversationSummaries([ANA], withSentAt, CONVERSATION_USERS, { now: NOW });
    const [rui] = buildConversationSummaries([RUI], withoutSentAt, CONVERSATION_USERS, {
      now: NOW,
    });

    expect(ana.timeLabel).toBe('Ontem');
    expect(rui.timeLabel).toBe('10:00');
  });

  it('ignora mensagens de conversas que ainda não se sabe de quem são', () => {
    const summaries = buildConversationSummaries(
      [ANA],
      [text('c-desconhecida', 'them', 'olá')],
      CONVERSATION_USERS,
      { now: NOW },
    );

    expect(summaries[0].lastMessagePreview).toBe('Toca para conversar');
  });

  it('quem está a escrever mostra "a escrever…" em vez da última mensagem', () => {
    const summaries = buildConversationSummaries(
      [ANA, RUI],
      [text('c-ana', 'them', 'olá'), text('c-rui', 'them', 'olá')],
      CONVERSATION_USERS,
      { typingConversations: new Set(['c-ana']), now: NOW },
    );
    const ana = summaries.find((summary) => summary.id === 'ana');
    const rui = summaries.find((summary) => summary.id === 'rui');

    expect(ana).toMatchObject({ lastMessagePreview: 'a escrever…', isTyping: true });
    expect(rui).toMatchObject({ lastMessagePreview: 'olá', isTyping: false });
  });
});

describe('initialsFor', () => {
  it('usa as iniciais das duas primeiras palavras', () => {
    expect(initialsFor('ana maria silva')).toBe('AM');
    expect(initialsFor('rui')).toBe('R');
  });
});
