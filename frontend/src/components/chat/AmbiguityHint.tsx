import { StyleSheet, Text } from 'react-native';

import { colors } from '../../theme/colors';

export function AmbiguityHint() {
  return (
    <Text style={styles.text}>
      O identificador só aparece quando tens mais do que um contacto com a mesma alcunha ou nome —
      ajuda a não confundires pessoas diferentes.
    </Text>
  );
}

const styles = StyleSheet.create({
  text: {
    color: colors.textMuted,
    fontSize: 12,
    lineHeight: 18,
  },
});
