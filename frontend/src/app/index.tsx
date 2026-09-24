import { Redirect, router } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ConversationList } from '../components/conversations/ConversationList';
import { ConversationsHeader } from '../components/conversations/ConversationsHeader';
import { LoadingState } from '../components/LoadingState';
import { useIdentity } from '../context/IdentityContext';
import { colors } from '../theme/colors';

export default function ConversationsScreen() {
  const identity = useIdentity();

  if (identity.loading) return <LoadingState />;
  if (!identity.authenticated) return <Redirect href="/login" />;

  return (
    <SafeAreaView style={styles.container} edges={['top', 'left', 'right']}>
      <View style={styles.header}>
        <ConversationsHeader />
      </View>

      {identity.otherUsers.length === 0 ? (
        <View style={styles.center}>
          <Text style={styles.waitingTitle}>És o {identity.displayName}</Text>
          <Text style={styles.waitingSubtitle}>
            Ainda não há mais ninguém registado neste servidor. Abre a app noutro dispositivo para
            aparecer aqui.
          </Text>
        </View>
      ) : (
        <View style={styles.list}>
          <ConversationList
            conversations={identity.otherUsers.map((user) => ({
              id: user.user_id,
              title: user.display_name,
              initials: initialsFor(user.display_name),
              lastMessagePreview: 'Toca para conversar',
              timeLabel: '',
            }))}
            onSelectConversation={(id) => router.push(`/conversation/${id}`)}
          />
        </View>
      )}
    </SafeAreaView>
  );
}

function initialsFor(name: string): string {
  return name
    .split(' ')
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 12,
  },
  list: {
    flex: 1,
    paddingHorizontal: 20,
    marginTop: 8,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingHorizontal: 32,
  },
  waitingTitle: {
    color: colors.textPrimary,
    fontSize: 18,
    fontWeight: '700',
  },
  waitingSubtitle: {
    color: colors.textSecondary,
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
  },
});
