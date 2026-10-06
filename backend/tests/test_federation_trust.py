import uuid

from app.federation import trust
from app.models.federated_server import TRUSTED


def _domain() -> str:
    return f"{uuid.uuid4().hex[:8]}.test"


def test_unknown_server_is_not_pinned() -> None:
    assert trust.pinned_server(_domain()) is None


def test_pin_stores_the_key_as_trusted() -> None:
    domain = _domain()

    row = trust.pin(domain, "ed25519:1", "chave-a")

    stored = trust.pinned_server(domain)
    assert stored is not None
    assert (row.domain, stored.key_id, stored.verify_key) == (domain, "ed25519:1", "chave-a")
    assert stored.trust_status == TRUSTED
    assert stored.changed_key is None
    assert stored.key_changed_at is None


def test_second_pin_keeps_the_first_key() -> None:
    domain = _domain()
    trust.pin(domain, "ed25519:1", "primeira")

    row = trust.pin(domain, "ed25519:1", "segunda")

    assert row.verify_key == "primeira"


def test_mark_key_changed_records_the_new_key_without_replacing_the_pinned_one() -> None:
    domain = _domain()
    trust.pin(domain, "ed25519:1", "original")

    trust.mark_key_changed(domain, "nova")

    stored = trust.pinned_server(domain)
    assert stored is not None
    assert stored.verify_key == "original"
    assert stored.changed_key == "nova"
    assert stored.key_changed_at is not None


def test_touch_updates_last_seen_only() -> None:
    domain = _domain()
    first = trust.pin(domain, "ed25519:1", "chave")

    trust.touch(domain)

    stored = trust.pinned_server(domain)
    assert stored is not None
    assert stored.last_seen_at > first.last_seen_at
    assert stored.first_seen_at == first.first_seen_at
