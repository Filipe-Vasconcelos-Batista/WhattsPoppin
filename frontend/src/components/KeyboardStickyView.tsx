import type { ReactNode } from 'react';
import { View } from 'react-native';

import { useKeyboardInset } from '../hooks/useKeyboardInset';

type KeyboardStickyViewProps = {
  children: ReactNode;
};
export function KeyboardStickyView({ children }: KeyboardStickyViewProps) {
  const keyboardInset = useKeyboardInset();

  return <View style={{ paddingBottom: keyboardInset }}>{children}</View>;
}
