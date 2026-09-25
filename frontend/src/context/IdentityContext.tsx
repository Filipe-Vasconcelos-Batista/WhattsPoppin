import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import { loginUser, registerUser, resumeSession, type UserSummary } from '../api/auth';
import { generateAndPublishDeviceKeys } from '../crypto/keys';
import {
  decryptIncoming,
  encryptForConversation,
  type IncomingEncryptedMessage,
} from '../crypto/messaging';
import { useSocketConnection } from '../hooks/useSocketConnection';
import { newClientMessageId } from '../messaging/clientMessageId';
import { createOutgoingQueue } from '../messaging/outgoingQueue';
import { advanceStatus } from '../messaging/status';
import { loadMessages, saveMessages } from '../storage/messageStore';
import { formatTimeNow } from '../utils/time';
import type { ChatMessage, MessageStatus } from '../types/chat';

const STORAGE_KEY = 'whattspoppin.device_token';
const UNDECRYPTABLE_TEXT = '[mensagem não pôde ser decifrada]';

type IncomingPayload =
  | ({
      type: 'message';
      message_id: string;
      conversation_id: string;
      client_message_id: string;
      sender_device_id: string;
    } & IncomingEncryptedMessage)
  | { type: 'sent'; client_message_id: string }
  | {
      type: 'receipt';
      message_id: string;
      status: 'delivered' | 'read';
      conversation_id: string;
      client_message_ids: string[];
    }
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
  markConversationRead: (conversationId: string) => void;
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
  markConversationRead: () => {},
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
  // Mensagens recebidas já tratadas, por `${sender_device_id}:${client_message_id}`
  // - o servidor reenvia o que não recebeu ack e quem envia pode reenviar da
  // outbox; decifrar a mesma mensagem duas vezes falharia (a chave já foi usada).
  const seenMessageIdsRef = useRef(new Set<string>());
  const sendRef = useRef<(payload: Record<string, unknown>) => boolean>(() => false);
  const messagesRef = useRef<ChatMessage[]>([]);

  const outgoingQueue = useMemo(
    () =>
      deviceId
        ? createOutgoingQueue({
            storageKey: `whattspoppin.outbox.${deviceId}`,
            encrypt: (conversationId, text) =>
              encryptForConversation(deviceId, conversationId, text),
            send: (payload) => sendRef.current(payload),
          })
        : null,
    [deviceId],
  );

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
    const storedMessages = await loadMessages(newUserId);
    seenMessageIdsRef.current = new Set(storedMessages.map((message) => message.id));
    setMessages(storedMessages);
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

  const updateMyStatus = useCallback((clientMessageIds: string[], status: MessageStatus) => {
    const ids = new Set(clientMessageIds);
    setMessages((prev) =>
      prev.map((message) =>
        message.kind === 'text' && message.authorId === 'me' && ids.has(message.id)
          ? { ...message, status: advanceStatus(message.status, status) }
          : message,
      ),
    );
  }, []);

  const handlePayload = useCallback(
    (raw: unknown) => {
      const payload = raw as IncomingPayload;

      if (payload.type === 'user_registered') {
        setOtherUsers((prev) =>
          prev.some((user) => user.user_id === payload.user.user_id)
            ? prev
            : [...prev, payload.user],
        );
        return;
      }

      if (payload.type === 'sent') {
        outgoingQueue?.confirmSent(payload.client_message_id);
        updateMyStatus([payload.client_message_id], 'sent');
        return;
      }

      if (payload.type === 'receipt') {
        updateMyStatus(payload.client_message_ids, payload.status);
        sendRef.current({ type: 'ack', message_ids: [payload.message_id] });
        return;
      }

      if (payload.type === 'message' && deviceId) {
        const ack = () => sendRef.current({ type: 'ack', message_ids: [payload.message_id] });
        const key = `${payload.sender_device_id}:${payload.client_message_id}`;

        if (seenMessageIdsRef.current.has(key)) {
          ack();
          return;
        }
        // Marcado antes de decifrar: uma segunda cópia que chegue entretanto
        // não é decifrada outra vez.
        seenMessageIdsRef.current.add(key);

        decryptIncoming(deviceId, payload.sender_device_id, payload)
          .catch((error: unknown) => {
            console.warn('Falha ao decifrar mensagem:', error);
            return UNDECRYPTABLE_TEXT;
          })
          .then((text) => {
            setMessages((prev) => [
              ...prev,
              {
                id: key,
                conversationId: payload.conversation_id,
                kind: 'text',
                authorId: 'them',
                text,
                timeLabel: formatTimeNow(),
                senderDeviceId: payload.sender_device_id,
                clientMessageId: payload.client_message_id,
              },
            ]);
            // Também quando não decifra: tentar de novo não mudaria nada.
            ack();
          });
      }
    },
    [deviceId, outgoingQueue, updateMyStatus],
  );

  const { send } = useSocketConnection(deviceId, handlePayload, () => {
    outgoingQueue?.onSocketOpen();
  });

  // Layout effect, não effect normal: os efeitos dos filhos (ex.: o ecrã da
  // conversa a marcar como lido) correm antes dos do pai, e leriam aqui a
  // lista de mensagens ainda antiga. Os layout effects correm todos antes.
  useLayoutEffect(() => {
    sendRef.current = send;
    messagesRef.current = messages;
  });

  useEffect(() => {
    if (!userId) return;
    saveMessages(userId, messages);
  }, [userId, messages]);

  function sendMessage(conversationId: string, text: string) {
    const clientMessageId = newClientMessageId();
    setMessages((prev) => [
      ...prev,
      {
        id: clientMessageId,
        conversationId,
        kind: 'text',
        authorId: 'me',
        text,
        timeLabel: formatTimeNow(),
        status: 'pending',
      },
    ]);
    // Fica na outbox até o servidor confirmar ("sent") - com o socket em
    // baixo espera, e sai quando ele abrir.
    outgoingQueue
      ?.enqueue({ clientMessageId, conversationId, text })
      .catch((error: unknown) => console.warn('Falha ao guardar mensagem na outbox:', error));
  }

  // Manda um recibo de leitura por cada device que enviou mensagens ainda não
  // marcadas como lidas nesta conversa. Só marca como enviado se o socket
  // estava aberto - senão tenta de novo na próxima vez.
  const markConversationRead = useCallback((conversationId: string) => {
    const bySender = new Map<string, string[]>();
    const readIds = new Set<string>();

    for (const message of messagesRef.current) {
      if (
        message.kind !== 'text' ||
        message.conversationId !== conversationId ||
        message.authorId === 'me' ||
        !message.senderDeviceId ||
        !message.clientMessageId ||
        message.readReceiptSent
      ) {
        continue;
      }
      const ids = bySender.get(message.senderDeviceId) ?? [];
      ids.push(message.clientMessageId);
      bySender.set(message.senderDeviceId, ids);
      readIds.add(message.id);
    }
    if (readIds.size === 0) return;

    const sent = sendRef.current({
      type: 'read',
      conversation_id: conversationId,
      receipts: [...bySender].map(([device_id, client_message_ids]) => ({
        device_id,
        client_message_ids,
      })),
    });
    if (!sent) return;

    setMessages((prev) =>
      prev.map((message) =>
        message.kind === 'text' && readIds.has(message.id)
          ? { ...message, readReceiptSent: true }
          : message,
      ),
    );
  }, []);

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
        markConversationRead,
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
