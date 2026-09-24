import { LinearGradient } from 'expo-linear-gradient';
import type { ReactNode } from 'react';
import { Pressable, StyleSheet } from 'react-native';

import { gradients } from '../theme/colors';

type GradientButtonProps = {
  onPress?: () => void;
  size?: number;
  children: ReactNode;
};

export function GradientButton({ onPress, size = 56, children }: GradientButtonProps) {
  return (
    <Pressable onPress={onPress} style={[styles.pressable, { borderRadius: size / 2 }]}>
      <LinearGradient
        colors={gradients.action}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={[styles.gradient, { width: size, height: size, borderRadius: size / 2 }]}
      >
        {children}
      </LinearGradient>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  pressable: {
    shadowColor: '#22D3EE',
    shadowOpacity: 0.5,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
  },
  gradient: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
