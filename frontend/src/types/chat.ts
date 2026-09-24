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

export type ChatMessage =
  | {
      id: string;
      kind: 'text';
      authorId: 'me' | string;
      text: string;
      timeLabel: string;
    }
  | {
      id: string;
      kind: 'sticker';
      authorId: 'me' | string;
      timeLabel: string;
    };
