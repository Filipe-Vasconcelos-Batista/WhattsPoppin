import { Redirect, router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { getOrCreateConversation } from '../../api/conversations';
import { ChatHeader } from '../../components/chat/ChatHeader';
import { KeyboardStickyView } from '../../components/KeyboardStickyView';
import { LoadingState } from '../../components/LoadingState';
import { MessageInputBar } from '../../components/chat/MessageInputBar';
import { MessageList } from '../../components/chat/MessageList';
import { useIdentity } from '../../context/IdentityContext';
import { useIsAppActive } from '../../hooks/useIsAppActive';
import { colors } from '../../theme/colors';
import type { Contact } from '../../types/chat';

export default function ConversationScreen() {
  const { id: otherUserId } = useLocalSearchParams<{ id: string }>();
  const identity = useIdentity();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const { rememberConversation } = identity;

  useEffect(() => {
    if (!identity.userId) return;
    let cancelled = false;

    getOrCreateConversation(identity.userId, otherUserId).then((id) => {
      rememberConversation(otherUserId, id);
      if (!cancelled) setConversationId(id);
    });

    return () => {
      cancelled = true;
    };
  }, [identity.userId, otherUserId, rememberConversation]);

  const { markConversationRead } = identity;
  const appActive = useIsAppActive();
  const conversationMessageCount = identity.messages.filter(
    (message) => message.conversationId === conversationId,
  ).length;

  useEffect(() => {
    if (conversationId && appActive) markConversationRead(conversationId);
  }, [conversationId, conversationMessageCount, appActive, markConversationRead]);

  if (identity.loading) return <LoadingState />;
  if (!identity.authenticated) return <Redirect href="/login" />;

  const otherUser = identity.otherUsers.find((user) => user.user_id === otherUserId);

  if (!otherUser || !conversationId) return <LoadingState />;

  const contact: Contact = {
    id: otherUser.user_id,
    displayName: otherUser.display_name,
    identifier: otherUser.user_id,
  };

  const messages = identity.messages.filter((message) => message.conversationId === conversationId);

  return (
    <SafeAreaView style={styles.container} edges={['top', 'left', 'right']}>
      <View style={styles.header}>
        <ChatHeader contact={contact} onBackPress={() => router.back()} />
      </View>

      <KeyboardAvoidingView
        style={styles.body}
        // web fica a cargo do KeyboardStickyView abaixo - o
        // KeyboardAvoidingView é só para nativo (iOS/Android)
        behavior={
          Platform.OS === 'web' ? undefined : Platform.select({ ios: 'padding', android: 'height' })
        }
        keyboardVerticalOffset={12}
      >
        <View style={styles.messages}>
          <MessageList messages={messages} />
        </View>

        <KeyboardStickyView>
          <View style={styles.inputBar}>
            <MessageInputBar onSend={(text) => identity.sendMessage(conversationId, text)} />
          </View>
        </KeyboardStickyView>
      </KeyboardAvoidingView>
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
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  body: {
    flex: 1,
  },
  messages: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 16,
  },
  inputBar: {
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
});
