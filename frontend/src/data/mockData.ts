import type { ChatMessage, Contact, ConversationSummary } from '../types/chat';

export const mockConversations: ConversationSummary[] = [
  {
    id: 'jonas',
    title: 'joao@amigo.servidor.pt',
    initials: 'JR',
    lastMessagePreview: 'Enviou uma figurinha',
    timeLabel: '14:32',
    unreadCount: 2,
  },
  {
    id: 'mariana',
    title: 'Mariana',
    initials: 'MS',
    lastMessagePreview: 'Vemo-nos sábado?',
    timeLabel: 'Ontem',
  },
  {
    id: 'retro-gaming',
    title: 'Grupo: Retro Gaming',
    initials: 'RG',
    lastMessagePreview: 'Pedro: alguém tem a rom?',
    timeLabel: 'Ter',
    isGroup: true,
  },
];

export const mockContactsById: Record<string, Contact> = {
  jonas: {
    id: 'jonas',
    displayName: 'João Ramos',
    nickname: 'Jonas',
    identifier: 'joao@amigo.servidor.pt',
    isAmbiguous: true,
  },
  mariana: {
    id: 'mariana',
    displayName: 'Mariana',
    identifier: 'mariana@oteuservidor.pt',
  },
};

export const mockMessagesByConversation: Record<string, ChatMessage[]> = {
  jonas: [
    {
      id: 'm1',
      kind: 'text',
      authorId: 'jonas',
      text: 'Olá! Já experimentei o servidor novo',
      timeLabel: '14:20',
    },
    {
      id: 'm2',
      kind: 'text',
      authorId: 'me',
      text: 'Boa! Ligação a correr bem?',
      timeLabel: '14:21',
    },
    {
      id: 'm3',
      kind: 'text',
      authorId: 'jonas',
      text: 'Sim, handshake fez-se sozinho na primeira mensagem',
      timeLabel: '14:22',
    },
    { id: 'm4', kind: 'sticker', authorId: 'jonas', timeLabel: '14:23' },
  ],
};
