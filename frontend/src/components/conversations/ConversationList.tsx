import { FlatList } from 'react-native';

import { ConversationListItem } from './ConversationListItem';
import type { ConversationSummary } from '../../types/chat';

type ConversationListProps = {
  conversations: ConversationSummary[];
  onSelectConversation?: (id: string) => void;
};

export function ConversationList({ conversations, onSelectConversation }: ConversationListProps) {
  return (
    <FlatList
      data={conversations}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => (
        <ConversationListItem conversation={item} onPress={() => onSelectConversation?.(item.id)} />
      )}
    />
  );
}
