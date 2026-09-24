import { Redirect, router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AuthHeader } from '../components/auth/AuthHeader';
import { AuthSwitchLink } from '../components/auth/AuthSwitchLink';
import { AuthTextField } from '../components/auth/AuthTextField';
import { LoadingState } from '../components/LoadingState';
import { PrimaryButton } from '../components/PrimaryButton';
import { useIdentity } from '../context/IdentityContext';
import { colors } from '../theme/colors';

export default function LoginScreen() {
  const identity = useIdentity();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (identity.loading) return <LoadingState />;
  if (identity.authenticated) return <Redirect href="/" />;

  async function handleSubmit() {
    setError(null);
    setSubmitting(true);
    try {
      await identity.login(username, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.form}>
        <AuthHeader subtitle="Liga-te ao teu servidor" />

        <AuthTextField
          label="Utilizador"
          value={username}
          onChangeText={setUsername}
          placeholder="tiago"
        />
        <AuthTextField
          label="Palavra-passe"
          value={password}
          onChangeText={setPassword}
          placeholder="••••••••"
          secureTextEntry
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <View style={styles.button}>
          <PrimaryButton label="Entrar" onPress={handleSubmit} loading={submitting} />
        </View>

        <AuthSwitchLink
          prompt="Ainda não tens conta?"
          actionLabel="Criar conta"
          onPress={() => router.push('/signup')}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: 'center',
  },
  form: {
    paddingHorizontal: 24,
    gap: 16,
  },
  button: {
    marginTop: 8,
  },
  error: {
    color: '#F87171',
    fontSize: 13,
  },
});
