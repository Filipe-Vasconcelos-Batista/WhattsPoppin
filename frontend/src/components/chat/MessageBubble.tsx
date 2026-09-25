import Ionicons from '@expo/vector-icons/Ionicons';
import { LinearGradient } from 'expo-linear-gradient';
import { StyleSheet, Text, View } from 'react-native';

import { colors, gradients } from '../../theme/colors';
import type { MessageStatus } from '../../types/chat';

type MessageBubbleProps = {
  text: string;
  timeLabel: string;
  isMine: boolean;
  status?: MessageStatus;
};

const STATUS_ICON: Record<MessageStatus, keyof typeof Ionicons.glyphMap> = {
  pending: 'time-outline',
  sent: 'checkmark',
  delivered: 'checkmark-done',
  read: 'checkmark-done',
};

const STATUS_LABEL: Record<MessageStatus, string> = {
  pending: 'Por enviar',
  sent: 'Enviada',
  delivered: 'Entregue',
  read: 'Lida',
};

export function MessageBubble({ text, timeLabel, isMine, status }: MessageBubbleProps) {
  return (
    <View style={[styles.wrapper, isMine ? styles.wrapperMine : styles.wrapperTheirs]}>
      {isMine ? (
        <LinearGradient
          colors={gradients.sentBubble}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.bubble}
        >
          <Text style={styles.text}>{text}</Text>
        </LinearGradient>
      ) : (
        <View style={[styles.bubble, styles.bubbleReceived]}>
          <Text style={styles.text}>{text}</Text>
        </View>
      )}
      <View style={[styles.meta, isMine ? styles.metaMine : styles.metaTheirs]}>
        <Text style={styles.time}>{timeLabel}</Text>
        {isMine && status ? (
          <Ionicons
            name={STATUS_ICON[status]}
            size={14}
            color={status === 'read' ? colors.accentCyan : colors.textMuted}
            accessibilityLabel={STATUS_LABEL[status]}
          />
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    maxWidth: '80%',
    marginBottom: 14,
  },
  wrapperMine: {
    alignSelf: 'flex-end',
  },
  wrapperTheirs: {
    alignSelf: 'flex-start',
  },
  bubble: {
    borderRadius: 18,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  bubbleReceived: {
    backgroundColor: colors.bubbleReceivedBg,
    borderWidth: 1,
    borderColor: colors.bubbleReceivedBorder,
  },
  text: {
    color: colors.textPrimary,
    fontSize: 15,
    lineHeight: 21,
  },
  meta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 4,
  },
  metaMine: {
    justifyContent: 'flex-end',
  },
  metaTheirs: {
    justifyContent: 'flex-start',
  },
  time: {
    fontSize: 11,
    color: colors.textMuted,
  },
});
