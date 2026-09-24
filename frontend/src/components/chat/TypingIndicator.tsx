import { useEffect, useState } from 'react';
import { Animated, StyleSheet, View } from 'react-native';

import { colors } from '../../theme/colors';

const DOT_COLORS = [colors.accentCyan, colors.accentCyan, colors.textMuted];

export function TypingIndicator() {
  const [dotOpacities] = useState(() => DOT_COLORS.map(() => new Animated.Value(0.3)));

  useEffect(() => {
    const animations = dotOpacities.map((opacity, index) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(index * 150),
          Animated.timing(opacity, { toValue: 1, duration: 300, useNativeDriver: true }),
          Animated.timing(opacity, { toValue: 0.3, duration: 300, useNativeDriver: true }),
          Animated.delay((DOT_COLORS.length - 1 - index) * 150),
        ]),
      ),
    );
    animations.forEach((animation) => animation.start());
    return () => animations.forEach((animation) => animation.stop());
  }, [dotOpacities]);

  return (
    <View style={styles.bubble}>
      {dotOpacities.map((opacity, index) => (
        <Animated.View
          key={index}
          style={[styles.dot, { backgroundColor: DOT_COLORS[index], opacity }]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  bubble: {
    flexDirection: 'row',
    alignSelf: 'flex-start',
    gap: 6,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 18,
    backgroundColor: colors.bubbleReceivedBg,
    borderWidth: 1,
    borderColor: colors.bubbleReceivedBorder,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
});
