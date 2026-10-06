import time
import uuid
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.config import SERVER_NAME
from app.federation import discovery, trust
from app.federation.keys import KEY_ID, public_key_b64, signing_key
from app.federation.signing import authorization_header
from app.models import FederatedServer
from app.models.federated_server import BLOCKED, TRUSTED
from tests.helpers import client

PING = "/_federation/v1/ping"


class FakeRemote:
    """Um servidor remoto: o domínio, a chave com que assina e o que o
    .well-known dele responde (por omissão, essa mesma chave)."""

    def __init__(self) -> None:
        self.domain = f"{uuid.uuid4().hex[:8]}.test"
        self.key = Ed25519PrivateKey.generate()
        self.well_known_requests = 0
        self.well_known_status = 200
        self.published_name = self.domain

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        assert request.url.host == self.domain.split(":")[0]
        assert request.url.path == "/.well-known/whattspoppin/server"
        self.well_known_requests += 1
        return httpx2.Response(
            self.well_known_status,
            json={
                "server_name": self.published_name,
                "versions": ["1"],
                "verify_keys": {KEY_ID: public_key_b64(self.key)},
            },
        )

    def headers(
        self,
        *,
        method: str = "GET",
        uri: str = PING,
        destination: str = SERVER_NAME,
        origin: str | None = None,
        ts: int | None = None,
        body: bytes = b"",
        key: Ed25519PrivateKey | None = None,
    ) -> dict[str, str]:
        header = authorization_header(
            key or self.key,
            KEY_ID,
            method,
            uri,
            origin or self.domain,
            destination,
            int(time.time()) if ts is None else ts,
            body,
        )
        return {"Authorization": header}


@pytest.fixture
def remote(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeRemote]:
    fake = FakeRemote()
    monkeypatch.setattr(discovery, "transport", httpx2.MockTransport(fake.handle))
    yield fake


def _row(domain: str) -> Any:
    return FederatedServer.get_or_none(FederatedServer.domain == domain)


def test_well_known_publishes_our_name_and_public_key() -> None:
    response = client.get("/.well-known/whattspoppin/server")

    assert response.status_code == 200
    assert response.json() == {
        "server_name": SERVER_NAME,
        "versions": ["1"],
        "verify_keys": {KEY_ID: public_key_b64(signing_key())},
    }


def test_ping_from_a_new_server_pins_its_key(remote: FakeRemote) -> None:
    response = client.get(PING, headers=remote.headers())

    assert response.status_code == 200
    assert response.json() == {"origin": remote.domain, "server_name": SERVER_NAME}
    assert remote.well_known_requests == 1
    row = _row(remote.domain)
    assert row.trust_status == TRUSTED
    assert (row.key_id, row.verify_key) == (KEY_ID, public_key_b64(remote.key))


def test_second_ping_does_not_fetch_the_key_again(remote: FakeRemote) -> None:
    assert client.get(PING, headers=remote.headers()).status_code == 200
    assert client.get(PING, headers=remote.headers()).status_code == 200

    assert remote.well_known_requests == 1


def test_missing_authorization_header_is_refused() -> None:
    assert client.get(PING).status_code == 401


def test_wrong_destination_is_refused(remote: FakeRemote) -> None:
    response = client.get(PING, headers=remote.headers(destination="outro.test"))

    assert response.status_code == 401
    assert remote.well_known_requests == 0


@pytest.mark.parametrize("offset", [-360, 360])
def test_timestamp_outside_the_window_is_refused(remote: FakeRemote, offset: int) -> None:
    response = client.get(PING, headers=remote.headers(ts=int(time.time()) + offset))

    assert response.status_code == 401
    assert remote.well_known_requests == 0


def test_timestamp_inside_the_window_is_accepted(remote: FakeRemote) -> None:
    response = client.get(PING, headers=remote.headers(ts=int(time.time()) - 240))

    assert response.status_code == 200


def test_tampered_uri_is_refused(remote: FakeRemote) -> None:
    response = client.get(PING, headers=remote.headers(uri="/_federation/v1/outro"))

    assert response.status_code == 401
    assert _row(remote.domain) is None


def test_tampered_query_is_refused(remote: FakeRemote) -> None:
    response = client.get(f"{PING}?x=2", headers=remote.headers(uri=f"{PING}?x=1"))

    assert response.status_code == 401


def test_tampered_body_is_refused(remote: FakeRemote) -> None:
    headers = remote.headers(body=b"original")

    response = client.request("GET", PING, headers=headers, content=b"outro")

    assert response.status_code == 401
    assert _row(remote.domain) is None


def test_tampered_method_is_refused(remote: FakeRemote) -> None:
    response = client.get(PING, headers=remote.headers(method="POST"))

    assert response.status_code == 401


def test_signature_from_a_key_the_server_does_not_publish_is_refused(remote: FakeRemote) -> None:
    impostor = Ed25519PrivateKey.generate()

    response = client.get(PING, headers=remote.headers(key=impostor))

    assert response.status_code == 401
    assert _row(remote.domain) is None


def test_well_known_with_another_server_name_is_refused(remote: FakeRemote) -> None:
    remote.published_name = "outro.test"

    response = client.get(PING, headers=remote.headers())

    assert response.status_code == 401
    assert _row(remote.domain) is None


def test_unreachable_well_known_is_refused(remote: FakeRemote) -> None:
    remote.well_known_status = 500

    response = client.get(PING, headers=remote.headers())

    assert response.status_code == 401
    assert _row(remote.domain) is None


def test_origin_equal_to_this_server_is_refused(remote: FakeRemote) -> None:
    response = client.get(PING, headers=remote.headers(origin=SERVER_NAME))

    assert response.status_code == 401
    assert remote.well_known_requests == 0


def test_origin_that_is_not_a_domain_is_refused(remote: FakeRemote) -> None:
    response = client.get(PING, headers=remote.headers(origin="Evil Host/../x"))

    assert response.status_code == 401
    assert remote.well_known_requests == 0


def test_blocked_server_is_refused_without_fetching_anything(remote: FakeRemote) -> None:
    trust.pin(remote.domain, KEY_ID, public_key_b64(remote.key))
    FederatedServer.update(trust_status=BLOCKED).where(
        FederatedServer.domain == remote.domain
    ).execute()

    response = client.get(PING, headers=remote.headers())

    assert response.status_code == 403
    assert remote.well_known_requests == 0


def test_changed_key_is_refused_and_recorded_without_replacing_the_pinned_one(
    remote: FakeRemote,
) -> None:
    original = public_key_b64(remote.key)
    assert client.get(PING, headers=remote.headers()).status_code == 200

    remote.key = Ed25519PrivateKey.generate()
    response = client.get(PING, headers=remote.headers())

    assert response.status_code == 401
    row = _row(remote.domain)
    assert row.verify_key == original
    assert row.changed_key == public_key_b64(remote.key)
    assert row.key_changed_at is not None


def test_forged_request_does_not_mark_a_change_when_the_published_key_is_the_pinned_one(
    remote: FakeRemote,
) -> None:
    assert client.get(PING, headers=remote.headers()).status_code == 200

    response = client.get(PING, headers=remote.headers(key=Ed25519PrivateKey.generate()))

    assert response.status_code == 401
    row = _row(remote.domain)
    assert row.changed_key is None
    assert row.key_changed_at is None
