import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Avatar } from '../Avatar';
import { UnreadBadge } from './UnreadBadge';
import { colorForId, colors } from '../../theme/colors';
import type { ConversationSummary } from '../../types/chat';

type ConversationListItemProps = {
  conversation: ConversationSummary;
  onPress?: () => void;
};

export function ConversationListItem({ conversation, onPress }: ConversationListItemProps) {
  return (
    <Pressable onPress={onPress} style={styles.row}>
      <Avatar initials={conversation.initials} color={colorForId(conversation.id)} />

      <View style={styles.middle}>
        <Text style={styles.title} numberOfLines={1}>
          {conversation.title}
        </Text>
        <Text
          style={[styles.preview, conversation.isTyping && styles.previewTyping]}
          numberOfLines={1}
        >
          {conversation.lastMessagePreview}
        </Text>
      </View>

      <View style={styles.right}>
        <Text style={styles.time}>{conversation.timeLabel}</Text>
        {conversation.unreadCount ? <UnreadBadge count={conversation.unreadCount} /> : null}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  middle: {
    flex: 1,
    gap: 4,
  },
  title: {
    color: colors.textPrimary,
    fontSize: 16,
    fontWeight: '600',
  },
  preview: {
    color: colors.textSecondary,
    fontSize: 14,
  },
  previewTyping: {
    color: colors.accentCyan,
  },
  right: {
    alignItems: 'flex-end',
    gap: 6,
  },
  time: {
    color: colors.textMuted,
    fontSize: 12,
  },
});
