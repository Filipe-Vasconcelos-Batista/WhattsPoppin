import { StyleSheet, Text, View } from 'react-native';

import { colors } from '../theme/colors';

type AvatarProps = {
  initials: string;
  color: string;
  size?: number;
};

export function Avatar({ initials, color, size = 48 }: AvatarProps) {
  return (
    <View
      style={[
        styles.circle,
        { width: size, height: size, borderRadius: size / 2, borderColor: color },
      ]}
    >
      <Text style={[styles.initials, { color, fontSize: size * 0.36 }]}>{initials}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  circle: {
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surface,
  },
  initials: {
    fontWeight: '600',
  },
});
