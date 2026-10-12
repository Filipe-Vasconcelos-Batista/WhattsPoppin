import uuid
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest

from app.federation import discovery, trust
from app.federation.keys import KEY_ID
from app.models import FederatedServer, User
from app.models.federated_server import BLOCKED
from app.services.remote_users import upsert_shadow_user
from tests.helpers import PASSWORD, add_contact, auth_headers, client, register
from tests.test_federation_auth import FakeRemote


@pytest.fixture
def remote(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeRemote]:
    fake = FakeRemote()
    monkeypatch.setattr(discovery, "transport", httpx2.MockTransport(fake.handle))
    yield fake


def _profile_uri(username: str) -> str:
    return f"/_federation/v1/users/{username}/profile"


def test_profile_of_a_local_user(remote: FakeRemote) -> None:
    alice = register()
    uri = _profile_uri(alice["username"])

    response = client.get(uri, headers=remote.headers(uri=uri))

    assert response.status_code == 200
    assert response.json() == {
        "identifier": alice["identifier"],
        "display_name": alice["display_name"],
    }


def test_profile_of_an_unknown_user_is_not_found(remote: FakeRemote) -> None:
    uri = _profile_uri("ninguem-aqui")

    assert client.get(uri, headers=remote.headers(uri=uri)).status_code == 404


def test_shadow_users_are_not_served_as_ours(remote: FakeRemote) -> None:
    username = f"sombra-{uuid.uuid4().hex[:8]}"
    upsert_shadow_user(username, "outro.test", "Sombra")
    uri = _profile_uri(username)

    assert client.get(uri, headers=remote.headers(uri=uri)).status_code == 404


def test_profile_needs_a_signed_request() -> None:
    alice = register()

    assert client.get(_profile_uri(alice["username"])).status_code == 401


class RemoteProfiles:
    def __init__(self) -> None:
        self.domain = f"{uuid.uuid4().hex[:8]}.test"
        self.status = 200
        self.body: Any = None
        self.requests: list[httpx2.Request] = []

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return httpx2.Response(self.status, json=self.body)


@pytest.fixture
def other_server(monkeypatch: pytest.MonkeyPatch) -> Iterator[RemoteProfiles]:
    fake = RemoteProfiles()
    monkeypatch.setattr(discovery, "transport", httpx2.MockTransport(fake.handle))
    yield fake


def _add(session: dict[str, Any], identifier: str) -> Any:
    return client.post("/contacts", headers=auth_headers(session), json={"identifier": identifier})


def _shadow(username: str, domain: str) -> Any:
    return User.get_or_none(User.username == username, User.domain == domain)


def test_adding_a_remote_user_creates_a_shadow_user(other_server: RemoteProfiles) -> None:
    alice = register()
    identifier = f"bob@{other_server.domain}"
    other_server.body = {"identifier": identifier, "display_name": "Bob"}

    contact = add_contact(alice, identifier)

    assert contact["identifier"] == identifier
    assert contact["display_name"] == "Bob"
    assert contact["status"] == "pending_outgoing"
    request = other_server.requests[0]
    assert str(request.url) == f"http://{other_server.domain}/_federation/v1/users/bob/profile"
    assert request.headers["authorization"].startswith("WP-Sig ")
    shadow = _shadow("bob", other_server.domain)
    assert str(shadow.id) == contact["user_id"]
    assert shadow.password_hash == ""


def test_adding_again_refreshes_the_display_name(other_server: RemoteProfiles) -> None:
    alice = register()
    identifier = f"bob@{other_server.domain}"
    other_server.body = {"identifier": identifier, "display_name": "Bob"}
    first = add_contact(alice, identifier)

    other_server.body = {"identifier": identifier, "display_name": "Bob Novo"}
    second = add_contact(alice, identifier)

    assert second["user_id"] == first["user_id"]
    assert second["display_name"] == "Bob Novo"


def test_a_profile_for_someone_else_is_refused(other_server: RemoteProfiles) -> None:
    alice = register()
    other_server.body = {"identifier": f"carol@{other_server.domain}", "display_name": "Carol"}

    assert _add(alice, f"bob@{other_server.domain}").status_code == 502
    assert _shadow("bob", other_server.domain) is None
    assert _shadow("carol", other_server.domain) is None


@pytest.mark.parametrize(
    "body", [None, [], {"display_name": "Bob"}, {"identifier": "x", "display_name": ""}]
)
def test_malformed_profiles_are_refused(other_server: RemoteProfiles, body: Any) -> None:
    alice = register()
    if isinstance(body, dict) and "identifier" in body:
        body = {**body, "identifier": f"bob@{other_server.domain}"}
    other_server.body = body

    assert _add(alice, f"bob@{other_server.domain}").status_code == 502


def test_unknown_remote_user_is_not_found(other_server: RemoteProfiles) -> None:
    alice = register()
    other_server.status = 404

    assert _add(alice, f"bob@{other_server.domain}").status_code == 404
    assert _shadow("bob", other_server.domain) is None


def test_unreachable_server_is_a_bad_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("recusado", request=request)

    monkeypatch.setattr(discovery, "transport", httpx2.MockTransport(refuse))
    alice = register()

    assert _add(alice, "bob@em-baixo.test").status_code == 502


def test_blocked_server_is_not_contacted(other_server: RemoteProfiles) -> None:
    alice = register()
    trust.pin(other_server.domain, KEY_ID, "chave")
    FederatedServer.update(trust_status=BLOCKED).where(
        FederatedServer.domain == other_server.domain
    ).execute()

    assert _add(alice, f"bob@{other_server.domain}").status_code == 502
    assert other_server.requests == []


def test_shadow_users_cannot_log_in(other_server: RemoteProfiles) -> None:
    alice = register()
    identifier = f"bob@{other_server.domain}"
    other_server.body = {"identifier": identifier, "display_name": "Bob"}
    add_contact(alice, identifier)

    response = client.post("/auth/login", json={"username": "bob", "password": PASSWORD})

    assert response.status_code == 401
