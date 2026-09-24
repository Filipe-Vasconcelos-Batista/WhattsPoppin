import { StyleSheet, Text, View } from 'react-native';

import { colors } from '../../theme/colors';

type StickerBubbleProps = {
  timeLabel: string;
};

export function StickerBubble({ timeLabel }: StickerBubbleProps) {
  return (
    <View style={styles.wrapper}>
      <View style={styles.placeholder}>
        <Text style={styles.label}>figurinha</Text>
      </View>
      <Text style={styles.time}>{timeLabel}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    alignSelf: 'flex-start',
    marginBottom: 14,
  },
  placeholder: {
    width: 130,
    height: 100,
    borderRadius: 18,
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: colors.bubbleReceivedBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    color: colors.textMuted,
    fontSize: 13,
  },
  time: {
    color: colors.textMuted,
    fontSize: 11,
    marginTop: 4,
  },
});
