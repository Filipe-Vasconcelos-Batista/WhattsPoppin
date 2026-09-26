import { useEffect, useRef, useState } from 'react';
import { Platform, StyleSheet, TextInput, View, type TextInputKeyPressEvent } from 'react-native';
import Ionicons from '@expo/vector-icons/Ionicons';

import { GradientButton } from '../GradientButton';
import { createTypingSignal, type TypingSignal } from '../../messaging/typingSignal';
import { colors } from '../../theme/colors';

type MessageInputBarProps = {
  onSend?: (text: string) => void;
  onTypingChange?: (typing: boolean) => void;
  onPickImage?: () => void;
  onPickEmoji?: () => void;
};

export function MessageInputBar({
  onSend,
  onTypingChange,
  onPickImage,
  onPickEmoji,
}: MessageInputBarProps) {
  const [text, setText] = useState('');
  const onTypingChangeRef = useRef(onTypingChange);
  const typingSignalRef = useRef<TypingSignal | null>(null);

  useEffect(() => {
    onTypingChangeRef.current = onTypingChange;
  });

  useEffect(() => {
    const signal = createTypingSignal((typing) => onTypingChangeRef.current?.(typing));
    typingSignalRef.current = signal;
    return () => signal.stop();
  }, []);

  function handleChangeText(value: string) {
    setText(value);
    typingSignalRef.current?.textChanged(value);
  }

  function handleSend() {
    const trimmed = text.trim();
    if (!trimmed) return;
    typingSignalRef.current?.stop();
    onSend?.(trimmed);
    setText('');
  }

  // Só em web: Enter envia, Shift+Enter quebra linha. Em mobile o teclado
  // não tem essa distinção, por isso mantém-se o comportamento normal
  // (Enter quebra linha, envio é sempre pelo botão).
  function handleKeyPress(event: TextInputKeyPressEvent) {
    if (Platform.OS !== 'web') return;

    const webEvent = event.nativeEvent as unknown as {
      key: string;
      shiftKey: boolean;
      preventDefault: () => void;
    };
    if (webEvent.key === 'Enter' && !webEvent.shiftKey) {
      webEvent.preventDefault();
      handleSend();
    }
  }

  return (
    <View style={styles.row}>
      <Ionicons name="happy-outline" size={24} color={colors.textSecondary} onPress={onPickEmoji} />
      <Ionicons name="image-outline" size={24} color={colors.textSecondary} onPress={onPickImage} />

      <TextInput
        value={text}
        onChangeText={handleChangeText}
        onKeyPress={handleKeyPress}
        placeholder="Escreve uma mensagem"
        placeholderTextColor={colors.textSecondary}
        style={styles.input}
        multiline
      />

      <GradientButton onPress={handleSend} size={44}>
        <Ionicons name="send" size={18} color="#fff" />
      </GradientButton>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  input: {
    flex: 1,
    color: colors.textPrimary,
    borderWidth: 1,
    borderColor: colors.bubbleReceivedBorder,
    borderRadius: 22,
    paddingHorizontal: 16,
    paddingVertical: 10,
    maxHeight: 100,
  },
});
