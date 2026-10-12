import { Redirect, router } from 'expo-router';
import { useEffect, useMemo } from 'react';
import { Platform, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ContactRequestList } from '../components/contacts/ContactRequestList';
import { ConversationList } from '../components/conversations/ConversationList';
import { ConversationsHeader } from '../components/conversations/ConversationsHeader';
import { FloatingActionButton } from '../components/FloatingActionButton';
import { LoadingState } from '../components/LoadingState';
import { useIdentity } from '../context/IdentityContext';
import { buildConversationSummaries, totalUnread } from '../messaging/conversationSummaries';
import { colors } from '../theme/colors';

export default function ConversationsScreen() {
  const identity = useIdentity();
  const { otherUsers, messages, conversationUsers, typingConversations } = identity;
  const summaries = useMemo(
    () =>
      buildConversationSummaries(otherUsers, messages, conversationUsers, { typingConversations }),
    [otherUsers, messages, conversationUsers, typingConversations],
  );
  const unread = totalUnread(summaries);

  useEffect(() => {
    if (Platform.OS !== 'web') return;
    document.title = unread > 0 ? `(${unread}) WhattsPoppin` : 'WhattsPoppin';
  }, [unread]);

  if (identity.loading) return <LoadingState />;
  if (!identity.authenticated) return <Redirect href="/login" />;

  function handleContactAction(action: Promise<void>) {
    action.catch((error: unknown) => console.warn('Falha ao responder ao pedido:', error));
  }

  return (
    <SafeAreaView style={styles.container} edges={['top', 'left', 'right']}>
      <View style={styles.header}>
        <ConversationsHeader onSettingsPress={() => router.push('/profile')} />
      </View>

      <View style={styles.requests}>
        <ContactRequestList
          requests={identity.contactRequests}
          onAccept={(userId) => handleContactAction(identity.acceptContact(userId))}
          onRemove={(userId) => handleContactAction(identity.removeContact(userId))}
        />
      </View>

      {identity.otherUsers.length === 0 ? (
        <View style={styles.center}>
          <Text style={styles.waitingTitle}>És o {identity.displayName}</Text>
          <Text style={styles.waitingSubtitle}>
            {`Ainda não tens contactos. Toca no + e adiciona alguém pelo identificador (o teu é ${identity.identifier}).`}
          </Text>
        </View>
      ) : (
        <View style={styles.list}>
          <ConversationList
            conversations={summaries}
            onSelectConversation={(id) => router.push(`/conversation/${id}`)}
          />
        </View>
      )}

      <View style={styles.fab}>
        <FloatingActionButton onPress={() => router.push('/add-contact')} />
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
    paddingHorizontal: 20,
    paddingTop: 12,
  },
  requests: {
    paddingHorizontal: 20,
    marginTop: 8,
  },
  list: {
    flex: 1,
    paddingHorizontal: 20,
    marginTop: 8,
  },
  fab: {
    position: 'absolute',
    right: 24,
    bottom: 32,
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
