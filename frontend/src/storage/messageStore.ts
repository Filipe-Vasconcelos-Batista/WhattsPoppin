import AsyncStorage from '@react-native-async-storage/async-storage';

import type { ChatMessage } from '../types/chat';

function storageKey(userId: string): string {
  return `whattspoppin.messages.${userId}`;
}

export async function loadMessages(userId: string): Promise<ChatMessage[]> {
  const raw = await AsyncStorage.getItem(storageKey(userId));
  if (!raw) return [];

  try {
    return JSON.parse(raw) as ChatMessage[];
  } catch {
    return [];
  }
}

export async function saveMessages(userId: string, messages: ChatMessage[]): Promise<void> {
  await AsyncStorage.setItem(storageKey(userId), JSON.stringify(messages));
}
