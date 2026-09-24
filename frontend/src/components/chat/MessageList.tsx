import { FlatList } from 'react-native';

import { MessageBubble } from './MessageBubble';
import { StickerBubble } from './StickerBubble';
import { TypingIndicator } from './TypingIndicator';
import type { ChatMessage } from '../../types/chat';

type MessageListProps = {
  messages: ChatMessage[];
  isOtherPersonTyping?: boolean;
};

export function MessageList({ messages, isOtherPersonTyping }: MessageListProps) {
  return (
    <FlatList
      data={messages}
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
      ListFooterComponent={isOtherPersonTyping ? <TypingIndicator /> : null}
    />
  );
}
