import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

import { loginUser, registerUser, resumeSession, type UserSummary } from '../api/auth';
import { generateAndPublishDeviceKeys } from '../crypto/keys';
import { useSocketConnection } from '../hooks/useSocketConnection';
import { loadMessages, saveMessages } from '../storage/messageStore';
import { formatTimeNow } from '../utils/time';
import type { ChatMessage } from '../types/chat';

const STORAGE_KEY = 'whattspoppin.device_token';

type IncomingPayload =
  | { type: 'message'; conversation_id: string; text: string }
  | { type: 'user_registered'; user: UserSummary };

type IdentityValue = {
  loading: boolean;
  authenticated: boolean;
  userId: string | null;
  deviceId: string | null;
  displayName: string | null;
  otherUsers: UserSummary[];
  messages: ChatMessage[];
  sendMessage: (conversationId: string, text: string) => void;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
};

const IdentityContext = createContext<IdentityValue>({
  loading: true,
  authenticated: false,
  userId: null,
  deviceId: null,
  displayName: null,
  otherUsers: [],
  messages: [],
  sendMessage: () => {},
  login: async () => {},
  register: async () => {},
});

export function IdentityProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState<string | null>(null);
  const [otherUsers, setOtherUsers] = useState<UserSummary[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      const storedToken = await AsyncStorage.getItem(STORAGE_KEY);
      if (!storedToken) {
        if (!cancelled) setLoading(false);
        return;
      }

      const session = await resumeSession(storedToken);
      if (cancelled) return;

      if (!session) {
        await AsyncStorage.removeItem(STORAGE_KEY);
        setLoading(false);
        return;
      }

      await applySession(
        session.token,
        session.user_id,
        session.device_id,
        session.display_name,
        session.other_users,
      );
      setLoading(false);
    }

    run();
    return () => {
      cancelled = true;
    };
  }, []);

  async function applySession(
    token: string,
    newUserId: string,
    newDeviceId: string,
    newDisplayName: string,
    newOtherUsers: UserSummary[],
  ) {
    setUserId(newUserId);
    setDeviceId(newDeviceId);
    setDisplayName(newDisplayName);
    setOtherUsers(newOtherUsers);
    setAuthenticated(true);
    setMessages(await loadMessages(newUserId));
    AsyncStorage.setItem(STORAGE_KEY, token);
  }

  async function login(username: string, password: string) {
    const session = await loginUser(username, password);
    await applySession(
      session.token,
      session.user_id,
      session.device_id,
      session.display_name,
      session.other_users,
    );
    generateAndPublishDeviceKeys(session.device_id, session.token).catch((error) => {
      console.warn('Falha ao gerar/publicar chaves E2E do dispositivo:', error);
    });
  }

  async function register(username: string, password: string) {
    const session = await registerUser(username, password);
    await applySession(
      session.token,
      session.user_id,
      session.device_id,
      session.display_name,
      session.other_users,
    );
    generateAndPublishDeviceKeys(session.device_id, session.token).catch((error) => {
      console.warn('Falha ao gerar/publicar chaves E2E do dispositivo:', error);
    });
  }

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

  useEffect(() => {
    if (!userId) return;
    saveMessages(userId, messages);
  }, [userId, messages]);

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
        authenticated,
        userId,
        deviceId,
        displayName,
        otherUsers,
        messages,
        sendMessage,
        login,
        register,
      }}
    >
      {children}
    </IdentityContext.Provider>
  );
}

export function useIdentity(): IdentityValue {
  return useContext(IdentityContext);
}
