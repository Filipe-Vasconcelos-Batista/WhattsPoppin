import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

import { bootstrapIdentity, type UserSummary } from '../api/identity';
import { useSocketConnection } from '../hooks/useSocketConnection';
import { formatTimeNow } from '../utils/time';
import type { ChatMessage } from '../types/chat';

const STORAGE_KEY = 'whattspoppin.device_token';

type IncomingPayload =
  | { type: 'message'; conversation_id: string; text: string }
  | { type: 'user_registered'; user: UserSummary };

type IdentityValue = {
  loading: boolean;
  error: string | null;
  userId: string | null;
  deviceId: string | null;
  displayName: string | null;
  otherUsers: UserSummary[];
  messages: ChatMessage[];
  sendMessage: (conversationId: string, text: string) => void;
};

const IdentityContext = createContext<IdentityValue>({
  loading: true,
  error: null,
  userId: null,
  deviceId: null,
  displayName: null,
  otherUsers: [],
  messages: [],
  sendMessage: () => {},
});

export function IdentityProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState<string | null>(null);
  const [otherUsers, setOtherUsers] = useState<UserSummary[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      try {
        const storedToken = await AsyncStorage.getItem(STORAGE_KEY);
        const identity = await bootstrapIdentity(storedToken);
        await AsyncStorage.setItem(STORAGE_KEY, identity.token);

        if (cancelled) return;
        setUserId(identity.user_id);
        setDeviceId(identity.device_id);
        setDisplayName(identity.display_name);
        setOtherUsers(identity.other_users);
        setLoading(false);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Erro desconhecido');
        setLoading(false);
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, []);

  const handlePayload = useCallback((raw: unknown) => {
    const payload = raw as IncomingPayload;

    if (payload.type === 'user_registered') {
      setOtherUsers((prev) =>
        prev.some((user) => user.user_id === payload.user.user_id) ? prev : [...prev, payload.user],
      );
      return;
    }

    if (payload.type === 'message') {
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-${Math.random()}`,
          conversationId: payload.conversation_id,
          kind: 'text',
          authorId: 'them',
          text: payload.text,
          timeLabel: formatTimeNow(),
        },
      ]);
    }
  }, []);

  const { send } = useSocketConnection(deviceId, handlePayload);

  function sendMessage(conversationId: string, text: string) {
    setMessages((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random()}`,
        conversationId,
        kind: 'text',
        authorId: 'me',
        text,
        timeLabel: formatTimeNow(),
      },
    ]);
    send({ conversation_id: conversationId, text });
  }

  return (
    <IdentityContext.Provider
      value={{
        loading,
        error,
        userId,
        deviceId,
        displayName,
        otherUsers,
        messages,
        sendMessage,
      }}
    >
      {children}
    </IdentityContext.Provider>
  );
}

export function useIdentity(): IdentityValue {
  return useContext(IdentityContext);
}
