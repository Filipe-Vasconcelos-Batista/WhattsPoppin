import { Redirect, router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AuthTextField } from '../components/auth/AuthTextField';
import { IconCircleButton } from '../components/IconCircleButton';
import { LoadingState } from '../components/LoadingState';
import { PrimaryButton } from '../components/PrimaryButton';
import { useIdentity } from '../context/IdentityContext';
import { colors } from '../theme/colors';

const RESULT_TEXT = {
  pending_outgoing: 'Pedido enviado. Aparece nas tuas conversas quando for aceite.',
  pending_incoming: 'Esta pessoa já te tinha enviado um pedido.',
  accepted: 'Já são contactos.',
} as const;

export default function AddContactScreen() {
  const identity = useIdentity();
  const [contactIdentifier, setContactIdentifier] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (identity.loading) return <LoadingState />;
  if (!identity.authenticated) return <Redirect href="/login" />;

  function handleChange(value: string) {
    setContactIdentifier(value);
    setError(null);
    setResult(null);
  }

  async function handleAdd() {
    setError(null);
    setResult(null);
    setSubmitting(true);
    try {
      const contact = await identity.addContact(contactIdentifier.trim());
      setResult(`${contact.display_name}: ${RESULT_TEXT[contact.status]}`);
      setContactIdentifier('');
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
        <Text style={styles.title}>Adicionar contacto</Text>
      </View>

      <View style={styles.body}>
        <AuthTextField
          label="Identificador"
          value={contactIdentifier}
          onChangeText={handleChange}
          placeholder="nome@servidor"
          helperText={`O teu é ${identity.identifier}. Para alguém deste servidor basta o nome.`}
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}
        {result ? <Text style={styles.result}>{result}</Text> : null}
      </View>

      <View style={styles.footer}>
        <PrimaryButton
          label="Enviar pedido"
          onPress={handleAdd}
          loading={submitting}
          disabled={!contactIdentifier.trim()}
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
  error: {
    color: '#F87171',
    fontSize: 13,
  },
  result: {
    color: colors.accentCyan,
    fontSize: 13,
  },
  footer: {
    paddingHorizontal: 24,
    paddingBottom: 24,
  },
});
