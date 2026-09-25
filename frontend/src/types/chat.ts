export type Contact = {
  id: string;
  displayName: string;
  nickname?: string;
  /** user@servidor - só aparece na UI quando isAmbiguous é verdadeiro */
  identifier: string;
  isAmbiguous?: boolean;
};

export type ConversationSummary = {
  id: string;
  title: string;
  initials: string;
  lastMessagePreview: string;
  timeLabel: string;
  unreadCount?: number;
  isGroup?: boolean;
};

/** Só nas minhas mensagens - avança por esta ordem e nunca recua. */
export type MessageStatus = 'pending' | 'sent' | 'delivered' | 'read';

export type ChatMessage =
  | {
      id: string;
      conversationId: string;
      kind: 'text';
      authorId: 'me' | string;
      text: string;
      timeLabel: string;
      status?: MessageStatus;
      /** Recebidas: device que enviou e id que ele deu à mensagem (para os recibos). */
      senderDeviceId?: string;
      clientMessageId?: string;
      readReceiptSent?: boolean;
    }
  | {
      id: string;
      conversationId: string;
      kind: 'sticker';
      authorId: 'me' | string;
      timeLabel: string;
    };
