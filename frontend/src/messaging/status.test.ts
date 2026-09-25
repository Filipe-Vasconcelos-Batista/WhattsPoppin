import { describe, it, expect } from 'vitest';

import { advanceStatus } from './status';
import { newClientMessageId } from './clientMessageId';

describe('advanceStatus', () => {
  it('avança pela ordem pending → sent → delivered → read', () => {
    expect(advanceStatus('pending', 'sent')).toBe('sent');
    expect(advanceStatus('sent', 'delivered')).toBe('delivered');
    expect(advanceStatus('delivered', 'read')).toBe('read');
  });

  it('pode saltar estados (ex.: read sem ter visto delivered)', () => {
    expect(advanceStatus('sent', 'read')).toBe('read');
  });

  it('nunca recua', () => {
    expect(advanceStatus('read', 'delivered')).toBe('read');
    expect(advanceStatus('delivered', 'sent')).toBe('delivered');
    expect(advanceStatus('sent', 'pending')).toBe('sent');
  });

  it('sem estado anterior, aceita o novo', () => {
    expect(advanceStatus(undefined, 'delivered')).toBe('delivered');
  });
});

describe('newClientMessageId', () => {
  it('gera UUIDs v4 válidos e diferentes', () => {
    const uuidV4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
    const ids = Array.from({ length: 50 }, newClientMessageId);
    for (const id of ids) expect(id).toMatch(uuidV4);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
