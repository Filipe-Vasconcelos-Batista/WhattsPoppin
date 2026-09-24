import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { IdentityProvider } from '../context/IdentityContext';
import { colors } from '../theme/colors';

export default function RootLayout() {
  return (
    <IdentityProvider>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: colors.background },
        }}
      />
    </IdentityProvider>
  );
}
