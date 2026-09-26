import { Redirect, router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AuthTextField } from '../components/auth/AuthTextField';
import { Avatar } from '../components/Avatar';
import { IconCircleButton } from '../components/IconCircleButton';
import { LoadingState } from '../components/LoadingState';
import { PrimaryButton } from '../components/PrimaryButton';
import { useIdentity } from '../context/IdentityContext';
import { initialsFor } from '../messaging/conversationSummaries';
import { colorForId, colors } from '../theme/colors';

export default function ProfileScreen() {
  const identity = useIdentity();
  const [name, setName] = useState(identity.displayName ?? '');
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (identity.loading) return <LoadingState />;
  if (!identity.authenticated || !identity.userId) return <Redirect href="/login" />;

  const unchanged = name.trim() === identity.displayName;

  function handleChangeName(value: string) {
    setName(value);
    setSaved(false);
  }

  async function handleSave() {
    setError(null);
    setSubmitting(true);
    try {
      await identity.updateDisplayName(name);
      setName(name.trim());
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <IconCircleButton name="chevron-back" onPress={() => router.back()} />
        <Text style={styles.title}>O meu perfil</Text>
      </View>

      <View style={styles.body}>
        <View style={styles.avatar}>
          <Avatar
            initials={initialsFor(identity.displayName ?? '')}
            color={colorForId(identity.userId)}
            size={96}
          />
        </View>

        <AuthTextField
          label="Nome de exibição"
          value={name}
          onChangeText={handleChangeName}
          helperText="Visível a todos os contactos. Não muda o nome de utilizador com que entras."
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}
        {saved ? <Text style={styles.saved}>Nome atualizado</Text> : null}
      </View>

      <View style={styles.footer}>
        <PrimaryButton
          label="Guardar"
          onPress={handleSave}
          loading={submitting}
          disabled={unchanged || !name.trim()}
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 20,
    paddingTop: 12,
  },
  title: {
    color: colors.textPrimary,
    fontSize: 20,
    fontWeight: '700',
  },
  body: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 24,
    gap: 16,
  },
  avatar: {
    alignItems: 'center',
    marginBottom: 8,
  },
  error: {
    color: '#F87171',
    fontSize: 13,
  },
  saved: {
    color: colors.accentCyan,
    fontSize: 13,
  },
  footer: {
    paddingHorizontal: 24,
    paddingBottom: 24,
  },
});
