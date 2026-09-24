import { StyleSheet } from 'react-native';
import Ionicons from '@expo/vector-icons/Ionicons';

import { GradientButton } from './GradientButton';

type FloatingActionButtonProps = {
  onPress?: () => void;
};

export function FloatingActionButton({ onPress }: FloatingActionButtonProps) {
  return (
    <GradientButton onPress={onPress} size={56}>
      <Ionicons name="add" size={28} color="#fff" style={styles.icon} />
    </GradientButton>
  );
}

const styles = StyleSheet.create({
  icon: {
    // ligeiro ajuste óptico do "+" no centro do círculo
    marginTop: -1,
  },
});
