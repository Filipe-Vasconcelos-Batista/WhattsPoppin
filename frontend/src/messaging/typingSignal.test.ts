import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import { createTypingSignal, TYPING_IDLE_MS, TYPING_REFRESH_MS } from './typingSignal';

function setup() {
  const emitted: boolean[] = [];
  const signal = createTypingSignal((typing) => emitted.push(typing), Date.now);
  return { emitted, signal };
}

describe('createTypingSignal', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('a primeira tecla manda "a escrever", as seguintes não repetem logo', () => {
    const { emitted, signal } = setup();

    signal.textChanged('o');
    signal.textChanged('ol');
    signal.textChanged('olá');

    expect(emitted).toEqual([true]);
  });

  it('sem teclas durante o tempo de inatividade, manda "parou"', () => {
    const { emitted, signal } = setup();

    signal.textChanged('olá');
    vi.advanceTimersByTime(TYPING_IDLE_MS - 1);
    expect(emitted).toEqual([true]);

    vi.advanceTimersByTime(1);
    expect(emitted).toEqual([true, false]);
  });

  it('a escrever sem parar, repete "a escrever" para o outro lado não expirar', () => {
    const { emitted, signal } = setup();

    signal.textChanged('a');
    for (let elapsed = 0; elapsed < TYPING_REFRESH_MS; elapsed += 1000) {
      vi.advanceTimersByTime(1000);
      signal.textChanged('a'.repeat(elapsed + 2));
    }

    expect(emitted).toEqual([true, true]);
  });

  it('enviar manda "parou" logo, e só uma vez', () => {
    const { emitted, signal } = setup();

    signal.textChanged('olá');
    signal.stop();
    signal.stop();
    vi.advanceTimersByTime(TYPING_IDLE_MS);

    expect(emitted).toEqual([true, false]);
  });

  it('apagar o texto todo conta como parar', () => {
    const { emitted, signal } = setup();

    signal.textChanged('olá');
    signal.textChanged('  ');

    expect(emitted).toEqual([true, false]);
  });

  it('stop sem ter começado não manda nada', () => {
    const { emitted, signal } = setup();

    signal.stop();

    expect(emitted).toEqual([]);
  });
});
