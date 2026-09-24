import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { colors } from '../theme/colors';

type LoadingStateProps = {
  label?: string;
};

export function LoadingState({ label = 'A ligar...' }: LoadingStateProps) {
  return (
    <View style={styles.container}>
      <ActivityIndicator color={colors.accentCyan} />
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  label: {
    color: colors.textSecondary,
    fontSize: 14,
  },
});
