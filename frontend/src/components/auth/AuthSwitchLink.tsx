import { Text, View, StyleSheet } from 'react-native';

import { colors } from '../../theme/colors';

type AuthSwitchLinkProps = {
  prompt: string;
  actionLabel: string;
  onPress: () => void;
};

export function AuthSwitchLink({ prompt, actionLabel, onPress }: AuthSwitchLinkProps) {
  return (
    <View style={styles.row}>
      <Text style={styles.prompt}>{prompt} </Text>
      <Text style={styles.action} onPress={onPress}>
        {actionLabel}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 20,
  },
  prompt: {
    color: colors.textSecondary,
    fontSize: 14,
  },
  action: {
    color: '#EC4899',
    fontSize: 14,
    fontWeight: '700',
  },
});
