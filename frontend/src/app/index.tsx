import { router } from 'expo-router';
import { StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ConversationList } from '../components/conversations/ConversationList';
import { ConversationsHeader } from '../components/conversations/ConversationsHeader';
import { FloatingActionButton } from '../components/FloatingActionButton';
import { SearchBar } from '../components/conversations/SearchBar';
import { colors } from '../theme/colors';
import { mockConversations } from '../data/mockData';

export default function ConversationsScreen() {
  return (
    <SafeAreaView style={styles.container} edges={['top', 'left', 'right']}>
      <View style={styles.header}>
        <ConversationsHeader />
        <SearchBar />
      </View>

      <View style={styles.list}>
        <ConversationList
          conversations={mockConversations}
          onSelectConversation={(id) => router.push(`/conversation/${id}`)}
        />
      </View>

      <View style={styles.fab}>
        <FloatingActionButton />
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
    gap: 16,
  },
  list: {
    flex: 1,
    paddingHorizontal: 20,
    marginTop: 8,
  },
  fab: {
    position: 'absolute',
    right: 20,
    bottom: 24,
  },
});
