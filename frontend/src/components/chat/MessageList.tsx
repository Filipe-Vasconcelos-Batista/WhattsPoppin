import { FlatList } from 'react-native';

import { MessageBubble } from './MessageBubble';
import { StickerBubble } from './StickerBubble';
import { TypingIndicator } from './TypingIndicator';
import type { ChatMessage } from '../../types/chat';

type MessageListProps = {
  messages: ChatMessage[];
  typing?: boolean;
};

export function MessageList({ messages, typing }: MessageListProps) {
  const reversedMessages = [...messages].reverse();

  return (
    <FlatList
      data={reversedMessages}
      inverted
      ListHeaderComponent={typing ? <TypingIndicator /> : null}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) =>
        item.kind === 'sticker' ? (
          <StickerBubble timeLabel={item.timeLabel} />
        ) : (
          <MessageBubble
            text={item.text}
            timeLabel={item.timeLabel}
            isMine={item.authorId === 'me'}
            status={item.status}
          />
        )
      }
    />
  );
}
