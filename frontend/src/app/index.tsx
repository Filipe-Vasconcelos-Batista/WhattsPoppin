import { Redirect, router } from 'expo-router';
import { useEffect, useMemo } from 'react';
import { Platform, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ConversationList } from '../components/conversations/ConversationList';
import { ConversationsHeader } from '../components/conversations/ConversationsHeader';
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
            conversations={summaries}
            onSelectConversation={(id) => router.push(`/conversation/${id}`)}
          />
        </View>
      )}
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
