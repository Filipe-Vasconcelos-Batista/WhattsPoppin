import type { UserSummary } from '../api/auth';
import type { ChatMessage, ConversationSummary } from '../types/chat';
import { formatListTime } from '../utils/time';

const EMPTY_PREVIEW = 'Toca para conversar';
const TYPING_PREVIEW = 'a escrever…';

type Latest = { message: ChatMessage; index: number; unread: number };

export function buildConversationSummaries(
  otherUsers: UserSummary[],
  messages: ChatMessage[],
  conversationUsers: Record<string, string>,
  {
    typingConversations = new Set<string>(),
    now = new Date(),
  }: { typingConversations?: ReadonlySet<string>; now?: Date } = {},
): ConversationSummary[] {
  const latestByUser = new Map<string, Latest>();
  const typingUsers = new Set(
    [...typingConversations].map((conversationId) => conversationUsers[conversationId]),
  );

  // O array está por ordem de chegada - a posição serve de ordem, também para
  // mensagens antigas sem sentAt.
  messages.forEach((message, index) => {
    const userId = conversationUsers[message.conversationId];
    if (!userId) return;
    const previous = latestByUser.get(userId);
    latestByUser.set(userId, {
      message,
      index,
      unread: (previous?.unread ?? 0) + (isUnread(message) ? 1 : 0),
    });
  });

  const summaries = otherUsers.map((user, order) => {
    const latest = latestByUser.get(user.user_id);
    const isTyping = typingUsers.has(user.user_id);
    const summary: ConversationSummary = {
      id: user.user_id,
      title: user.display_name,
      initials: initialsFor(user.display_name),
      lastMessagePreview: isTyping
        ? TYPING_PREVIEW
        : latest
          ? previewFor(latest.message)
          : EMPTY_PREVIEW,
      timeLabel: latest ? timeFor(latest.message, now) : '',
      unreadCount: latest?.unread,
      isTyping,
    };
    return { summary, rank: latest ? latest.index : -1, order };
  });

  summaries.sort((a, b) => b.rank - a.rank || a.order - b.order);
  return summaries.map(({ summary }) => summary);
}

export function totalUnread(summaries: ConversationSummary[]): number {
  return summaries.reduce((total, summary) => total + (summary.unreadCount ?? 0), 0);
}

export function initialsFor(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

function isUnread(message: ChatMessage): boolean {
  if (message.authorId === 'me' || message.kind !== 'text') return false;
  // Mensagens de antes do "seen" existir contam como vistas se já saiu recibo.
  return !message.seen && !message.readReceiptSent;
}

function previewFor(message: ChatMessage): string {
  const text = message.kind === 'text' ? message.text : 'Enviou uma figurinha';
  return message.authorId === 'me' ? `Tu: ${text}` : text;
}

function timeFor(message: ChatMessage, now: Date): string {
  return message.sentAt === undefined ? message.timeLabel : formatListTime(message.sentAt, now);
}
