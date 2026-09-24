import { FlatList } from 'react-native';

import { MessageBubble } from './MessageBubble';
import { StickerBubble } from './StickerBubble';
import type { ChatMessage } from '../../types/chat';

type MessageListProps = {
  messages: ChatMessage[];
};

export function MessageList({ messages }: MessageListProps) {
  // invertida: fica sempre ancorada à mensagem mais recente, junto à caixa
  // de escrever - como em qualquer app de chat, em vez de desenhar do topo
  // para baixo e deixar o vazio em baixo.
  const reversedMessages = [...messages].reverse();

  return (
    <FlatList
      data={reversedMessages}
      inverted
      keyExtractor={(item) => item.id}
      renderItem={({ item }) =>
        item.kind === 'sticker' ? (
          <StickerBubble timeLabel={item.timeLabel} />
        ) : (
          <MessageBubble
            text={item.text}
            timeLabel={item.timeLabel}
            isMine={item.authorId === 'me'}
          />
        )
      }
    />
  );
}
