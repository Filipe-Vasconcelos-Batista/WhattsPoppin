import { Redirect, router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@expo/vector-icons/Ionicons';

import { AuthHeader } from '../components/auth/AuthHeader';
import { AuthSwitchLink } from '../components/auth/AuthSwitchLink';
import { AuthTextField } from '../components/auth/AuthTextField';
import { LoadingState } from '../components/LoadingState';
import { PrimaryButton } from '../components/PrimaryButton';
import { useIdentity } from '../context/IdentityContext';
import { colors } from '../theme/colors';

const MIN_PASSWORD_LENGTH = 12;

export default function SignupScreen() {
  const identity = useIdentity();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (identity.loading) return <LoadingState />;
  if (identity.authenticated) return <Redirect href="/" />;

  async function handleSubmit() {
    setError(null);

    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`A password tem de ter pelo menos ${MIN_PASSWORD_LENGTH} caracteres`);
      return;
    }
    if (password !== confirmPassword) {
      setError('As passwords não coincidem');
      return;
    }

    setSubmitting(true);
    try {
      await identity.register(username, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <Ionicons
        name="chevron-back"
        size={24}
        color={colors.accentCyan}
        style={styles.back}
        onPress={() => router.back()}
      />

      <View style={styles.form}>
        <AuthHeader subtitle="Cria a tua conta neste servidor" />

        <AuthTextField
          label="Nome de utilizador"
          value={username}
          onChangeText={setUsername}
          placeholder="tiago"
        />
        <AuthTextField
          label="Palavra-passe"
          value={password}
          onChangeText={setPassword}
          placeholder={`mínimo ${MIN_PASSWORD_LENGTH} caracteres`}
          secureTextEntry
        />
        <AuthTextField
          label="Confirmar palavra-passe"
          value={confirmPassword}
          onChangeText={setConfirmPassword}
          placeholder="••••••••••••"
          secureTextEntry
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <View style={styles.button}>
          <PrimaryButton label="Criar conta" onPress={handleSubmit} loading={submitting} />
        </View>

        <AuthSwitchLink
          prompt="Já tens conta?"
          actionLabel="Entrar"
          onPress={() => router.push('/login')}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  back: {
    marginTop: 12,
    marginLeft: 20,
  },
  form: {
    flex: 1,
    justifyContent: 'center',
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
