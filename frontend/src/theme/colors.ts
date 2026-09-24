export const colors = {
  background: '#0A0E1A',
  surface: '#0F1524',
  surfaceBorder: '#1B2436',
  divider: 'rgba(255, 255, 255, 0.06)',

  accentCyan: '#22D3EE',

  textPrimary: '#F5F7FA',
  textSecondary: '#8B93A7',
  textMuted: '#5B6478',

  bubbleReceivedBg: '#101828',
  bubbleReceivedBorder: 'rgba(34, 211, 238, 0.35)',

  unreadBadge: '#EC4899',
} as const;

export const avatarPalette = [
  '#22D3EE',
  '#A855F7',
  '#EC4899',
  '#34D399',
  '#FB923C',
  '#FACC15',
] as const;

export const gradients = {
  sentBubble: ['#EC4899', '#A855F7'] as const,
  action: ['#d2d7d8', '#8B5CF6'] as const,
};

export function colorForId(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i += 1) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  }
  return avatarPalette[hash % avatarPalette.length];
}
