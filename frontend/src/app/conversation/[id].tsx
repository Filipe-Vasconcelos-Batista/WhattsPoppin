import { router, useLocalSearchParams } from 'expo-router';
import { KeyboardAvoidingView, Platform, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AmbiguityHint } from '../../components/chat/AmbiguityHint';
import { ChatHeader } from '../../components/chat/ChatHeader';
import { MessageInputBar } from '../../components/chat/MessageInputBar';
import { MessageList } from '../../components/chat/MessageList';
import { colors } from '../../theme/colors';
import { mockContactsById, mockMessagesByConversation } from '../../data/mockData';

export default function ConversationScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const contact = mockContactsById[id];
  const messages = mockMessagesByConversation[id] ?? [];

  if (!contact) return null;

  return (
    <SafeAreaView style={styles.container} edges={['top', 'left', 'right']}>
      <View style={styles.header}>
        <ChatHeader contact={contact} onBackPress={() => router.back()} />
        {contact.isAmbiguous ? <AmbiguityHint /> : null}
      </View>

      <KeyboardAvoidingView
        style={styles.body}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={12}
      >
        <View style={styles.messages}>
          <MessageList messages={messages} isOtherPersonTyping />
        </View>

        <View style={styles.inputBar}>
          <MessageInputBar />
        </View>
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
    gap: 10,
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
