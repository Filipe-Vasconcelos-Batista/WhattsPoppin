import { describe, it, expect } from 'vitest';

import type { ContactSummary } from '../api/contacts';
import { applyContact, removeFromLists, renameInLists, type ContactLists } from './contactLists';

const ANA = { user_id: 'ana', display_name: 'Ana', identifier: 'ana@test.local' };
const RUI = { user_id: 'rui', display_name: 'Rui', identifier: 'rui@outro.test' };

function contact(
  user: typeof ANA,
  status: ContactSummary['status'],
  extra: Partial<ContactSummary> = {},
): ContactSummary {
  return { ...user, status, ...extra };
}

const EMPTY: ContactLists = { otherUsers: [], contactRequests: [] };

describe('applyContact', () => {
  it('um pedido novo vai para os pedidos', () => {
    const lists = applyContact(EMPTY, contact(RUI, 'pending_incoming'));

    expect(lists.otherUsers).toEqual([]);
    expect(lists.contactRequests).toEqual([contact(RUI, 'pending_incoming')]);
  });

  it('aceite sai dos pedidos e entra na lista, sem o status', () => {
    const pending = applyContact(EMPTY, contact(RUI, 'pending_outgoing'));

    const lists = applyContact(pending, contact(RUI, 'accepted', { conversation_id: 'c-rui' }));

    expect(lists.contactRequests).toEqual([]);
    expect(lists.otherUsers).toEqual([{ ...RUI, conversation_id: 'c-rui' }]);
  });

  it('um contacto removido do outro lado volta a pendente e sai da lista', () => {
    const lists = applyContact(
      { otherUsers: [ANA], contactRequests: [] },
      contact(ANA, 'pending_outgoing'),
    );

    expect(lists.otherUsers).toEqual([]);
    expect(lists.contactRequests).toEqual([contact(ANA, 'pending_outgoing')]);
  });

  it('atualiza sem duplicar', () => {
    const once = applyContact(EMPTY, contact(RUI, 'pending_incoming'));

    const twice = applyContact(once, contact(RUI, 'pending_incoming', { display_name: 'Rui S' }));

    expect(twice.contactRequests).toHaveLength(1);
    expect(twice.contactRequests[0].display_name).toBe('Rui S');
  });
});

describe('removeFromLists', () => {
  it('tira o utilizador das duas listas', () => {
    const lists = { otherUsers: [ANA], contactRequests: [contact(RUI, 'pending_incoming')] };

    expect(removeFromLists(lists, 'ana').otherUsers).toEqual([]);
    expect(removeFromLists(lists, 'rui').contactRequests).toEqual([]);
  });
});

describe('renameInLists', () => {
  it('muda o nome onde quer que o utilizador esteja', () => {
    const lists = { otherUsers: [ANA], contactRequests: [contact(RUI, 'pending_incoming')] };

    const renamed = renameInLists(renameInLists(lists, 'ana', 'Ana S'), 'rui', 'Rui S');

    expect(renamed.otherUsers[0].display_name).toBe('Ana S');
    expect(renamed.contactRequests[0].display_name).toBe('Rui S');
  });
});
