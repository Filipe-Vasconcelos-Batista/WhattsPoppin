export const TYPING_IDLE_MS = 3000;
export const TYPING_REFRESH_MS = 3000;
// Maior que o TYPING_REFRESH_MS, senão quem recebe esconde o indicador entre
// dois "a escrever" seguidos.
export const TYPING_EXPIRE_MS = 5000;

export type TypingSignal = {
  textChanged: (text: string) => void;
  stop: () => void;
};

export function createTypingSignal(
  emit: (typing: boolean) => void,
  now: () => number = Date.now,
): TypingSignal {
  let typing = false;
  let lastSentAt = 0;
  let idleTimer: ReturnType<typeof setTimeout> | null = null;

  function clearIdleTimer() {
    if (idleTimer) clearTimeout(idleTimer);
    idleTimer = null;
  }

  function stop() {
    clearIdleTimer();
    if (!typing) return;
    typing = false;
    emit(false);
  }

  function textChanged(text: string) {
    if (!text.trim()) {
      stop();
      return;
    }
    // Repetido de tempos a tempos: se um "parou" ou um "a escrever" se perder,
    // quem recebe acerta sozinho em poucos segundos.
    if (!typing || now() - lastSentAt >= TYPING_REFRESH_MS) {
      typing = true;
      lastSentAt = now();
      emit(true);
    }
    clearIdleTimer();
    idleTimer = setTimeout(stop, TYPING_IDLE_MS);
  }

  return { textChanged, stop };
}
