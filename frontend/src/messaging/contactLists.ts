import type { UserSummary } from '../api/auth';
import type { ContactSummary } from '../api/contacts';

export type ContactLists = {
  otherUsers: UserSummary[];
  contactRequests: ContactSummary[];
};

function withoutUser<T extends UserSummary>(users: T[], userId: string): T[] {
  return users.filter((user) => user.user_id !== userId);
}

function upsert<T extends UserSummary>(users: T[], updated: T): T[] {
  return users.some((user) => user.user_id === updated.user_id)
    ? users.map((user) => (user.user_id === updated.user_id ? updated : user))
    : [...users, updated];
}

export function applyContact(lists: ContactLists, contact: ContactSummary): ContactLists {
  if (contact.status === 'accepted') {
    const { status: _status, ...user } = contact;
    return {
      otherUsers: upsert(lists.otherUsers, user),
      contactRequests: withoutUser(lists.contactRequests, contact.user_id),
    };
  }
  return {
    otherUsers: withoutUser(lists.otherUsers, contact.user_id),
    contactRequests: upsert(lists.contactRequests, contact),
  };
}

export function removeFromLists(lists: ContactLists, userId: string): ContactLists {
  return {
    otherUsers: withoutUser(lists.otherUsers, userId),
    contactRequests: withoutUser(lists.contactRequests, userId),
  };
}

export function renameInLists(
  lists: ContactLists,
  userId: string,
  displayName: string,
): ContactLists {
  const rename = <T extends UserSummary>(users: T[]): T[] =>
    users.map((user) => (user.user_id === userId ? { ...user, display_name: displayName } : user));
  return {
    otherUsers: rename(lists.otherUsers),
    contactRequests: rename(lists.contactRequests),
  };
}
