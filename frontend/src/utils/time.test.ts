import { describe, it, expect } from 'vitest';

import { formatListTime } from './time';

// Quinta, 24 set 2026, 15:00 (hora local)
const NOW = new Date(2026, 8, 24, 15, 0);

describe('formatListTime', () => {
  it('hoje mostra a hora', () => {
    expect(formatListTime(new Date(2026, 8, 24, 9, 5).getTime(), NOW)).toBe('09:05');
  });

  it('ontem mostra "Ontem", mesmo pouco antes da meia-noite', () => {
    expect(formatListTime(new Date(2026, 8, 23, 23, 59).getTime(), NOW)).toBe('Ontem');
  });

  it('na última semana mostra o dia', () => {
    expect(formatListTime(new Date(2026, 8, 22, 10, 0).getTime(), NOW)).toBe('Ter');
    expect(formatListTime(new Date(2026, 8, 18, 10, 0).getTime(), NOW)).toBe('Sex');
  });

  it('antes disso mostra a data', () => {
    expect(formatListTime(new Date(2026, 8, 3, 10, 0).getTime(), NOW)).toBe('03/09');
  });
});
