import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from app.db import db
from app.models import Contact, User
from app.models.contact import ACCEPTED, PENDING_INCOMING, PENDING_OUTGOING
from app.services.identifiers import is_local
from app.services.users import UserSummary, summary_of


class ContactError(Exception):
    pass


class ContactNotFoundError(Exception):
    pass


@dataclass
class ContactSummary(UserSummary):
    status: str = ACCEPTED


def _row(owner_id: uuid.UUID, contact_id: uuid.UUID) -> Contact | None:
    return Contact.get_or_none(Contact.owner == owner_id, Contact.contact == contact_id)


def _set(owner_id: uuid.UUID, contact_id: uuid.UUID, status: str) -> None:
    now = datetime.now(UTC)
    (
        Contact.insert(
            owner=owner_id, contact=contact_id, status=status, created_at=now, updated_at=now
        )
        .on_conflict(
            conflict_target=[Contact.owner, Contact.contact],
            update={Contact.status: status, Contact.updated_at: now},
        )
        .execute()
    )


def _delete(owner_id: uuid.UUID, contact_id: uuid.UUID) -> None:
    (
        Contact.delete()  # type: ignore[misc]
        .where(Contact.owner == owner_id, Contact.contact == contact_id)
        .execute()
    )


def request_contact(owner_id: uuid.UUID, contact_id: uuid.UUID) -> str:
    if owner_id == contact_id:
        raise ContactError("Não te podes adicionar a ti próprio")
    contact = User.get_or_none(User.id == contact_id)
    if contact is None:
        raise ContactNotFoundError
    local = is_local(contact.domain)

    with db.atomic():
        mine = _row(owner_id, contact_id)
        if mine is not None and mine.status != PENDING_INCOMING:
            return str(mine.status)

        theirs = _row(contact_id, owner_id) if local else None
        if mine is not None or (theirs is not None and theirs.status != PENDING_INCOMING):
            _set(owner_id, contact_id, ACCEPTED)
            if theirs is not None:
                _set(contact_id, owner_id, ACCEPTED)
            return ACCEPTED

        # Para outro servidor, o pedido só lá chega com a entrega federada (F6).
        _set(owner_id, contact_id, PENDING_OUTGOING)
        if local:
            _set(contact_id, owner_id, PENDING_INCOMING)
        return PENDING_OUTGOING


def accept_contact(owner_id: uuid.UUID, contact_id: uuid.UUID) -> str:
    mine = _row(owner_id, contact_id)
    if mine is None or mine.status != PENDING_INCOMING:
        raise ContactNotFoundError
    return request_contact(owner_id, contact_id)


def remove_contact(owner_id: uuid.UUID, contact_id: uuid.UUID) -> None:
    with db.atomic():
        mine = _row(owner_id, contact_id)
        if mine is None:
            raise ContactNotFoundError
        _delete(owner_id, contact_id)

        theirs = _row(contact_id, owner_id)
        if theirs is None:
            return
        if mine.status == PENDING_OUTGOING and theirs.status == PENDING_INCOMING:
            _delete(contact_id, owner_id)
        elif theirs.status == ACCEPTED:
            _set(contact_id, owner_id, PENDING_OUTGOING)


def are_contacts(user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> bool:
    mine = _row(user_a_id, user_b_id)
    if mine is None or mine.status != ACCEPTED:
        return False
    other = User.get_or_none(User.id == user_b_id)
    if other is None:
        return False
    # Um contacto remoto só tem o nosso lado aqui; o dele vive no servidor dele.
    if not is_local(other.domain):
        return True
    theirs = _row(user_b_id, user_a_id)
    return theirs is not None and theirs.status == ACCEPTED


def contact_summary(owner_id: uuid.UUID, contact_id: uuid.UUID) -> ContactSummary | None:
    row = _row(owner_id, contact_id)
    if row is None:
        return None
    return _summary(row, owner_id)


def list_contacts(owner_id: uuid.UUID) -> list[ContactSummary]:
    rows = (
        Contact.select(Contact, User)
        .join(User, on=(Contact.contact == User.id))
        .where(Contact.owner == owner_id)
        .order_by(Contact.created_at)
    )
    return [_summary(row, owner_id) for row in rows]


def _summary(row: Contact, owner_id: uuid.UUID) -> ContactSummary:
    summary = summary_of(row.contact, owner_id)
    return ContactSummary(**vars(summary), status=row.status)


def watcher_ids(user_id: uuid.UUID) -> list[uuid.UUID]:
    query = Contact.select(Contact.owner).where(Contact.contact == user_id)
    return list(query.scalars())
