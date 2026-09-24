import { StyleSheet, Text, View } from 'react-native';

import { IconCircleButton } from '../IconCircleButton';
import { colors } from '../../theme/colors';

type ConversationsHeaderProps = {
  onSettingsPress?: () => void;
};

export function ConversationsHeader({ onSettingsPress }: ConversationsHeaderProps) {
  return (
    <View style={styles.row}>
      <Text style={styles.title}>Conversas</Text>
      <IconCircleButton name="settings-outline" onPress={onSettingsPress} />
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  title: {
    color: colors.textPrimary,
    fontSize: 28,
    fontWeight: '700',
  },
});
