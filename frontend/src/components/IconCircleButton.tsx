import type { ComponentProps } from 'react';
import { Pressable, StyleSheet } from 'react-native';
import Ionicons from '@expo/vector-icons/Ionicons';

import { colors } from '../theme/colors';

type IconCircleButtonProps = {
  name: ComponentProps<typeof Ionicons>['name'];
  onPress?: () => void;
  color?: string;
  size?: number;
};

export function IconCircleButton({
  name,
  onPress,
  color = colors.accentCyan,
  size = 40,
}: IconCircleButtonProps) {
  return (
    <Pressable
      onPress={onPress}
      style={[
        styles.circle,
        { width: size, height: size, borderRadius: size / 2, borderColor: color },
      ]}
    >
      <Ionicons name={name} size={size * 0.5} color={color} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  circle: {
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
