import { LinearGradient } from 'expo-linear-gradient';
import { StyleSheet, Text, View } from 'react-native';

import { colors, gradients } from '../../theme/colors';

type MessageBubbleProps = {
  text: string;
  timeLabel: string;
  isMine: boolean;
};

export function MessageBubble({ text, timeLabel, isMine }: MessageBubbleProps) {
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
      <Text style={[styles.time, isMine ? styles.timeMine : styles.timeTheirs]}>{timeLabel}</Text>
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
  time: {
    fontSize: 11,
    marginTop: 4,
  },
  timeMine: {
    color: colors.textMuted,
    textAlign: 'right',
  },
  timeTheirs: {
    color: colors.textMuted,
  },
});
