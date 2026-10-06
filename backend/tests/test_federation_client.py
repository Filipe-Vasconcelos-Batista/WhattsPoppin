"""O cliente de saída e o `federation_origin` têm de concordar: o que um assina
o outro tem de aceitar. Aqui este servidor (`test.local`) faz-se passar por
`client.test` e o pedido que envia é reenviado ao próprio TestClient."""

import asyncio
import uuid
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest

from app.core.config import SERVER_NAME
from app.federation import client as federation_client
from app.federation import discovery, trust
from app.federation.client import FederationRequestError, federation_request
from app.federation.keys import KEY_ID, public_key_b64, signing_key
from app.models import FederatedServer
from app.models.federated_server import BLOCKED
from tests.helpers import client

SENDER = "client.test"


class Wire:
    """Rede falsa: o .well-known do remetente e a captura do que ele envia."""

    def __init__(self) -> None:
        self.sent: list[httpx2.Request] = []
        self.reply_status = 200

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/.well-known/whattspoppin/server":
            return httpx2.Response(
                200,
                json={
                    "server_name": SENDER,
                    "versions": ["1"],
                    "verify_keys": {KEY_ID: public_key_b64(signing_key())},
                },
            )
        self.sent.append(request)
        return httpx2.Response(self.reply_status, json={"ok": True})


@pytest.fixture
def wire(monkeypatch: pytest.MonkeyPatch) -> Iterator[Wire]:
    fake = Wire()
    monkeypatch.setattr(discovery, "transport", httpx2.MockTransport(fake.handle))
    monkeypatch.setattr(federation_client, "SERVER_NAME", SENDER)
    yield fake


def _send(destination: str, path: str = "/_federation/v1/ping", **kwargs: Any) -> httpx2.Response:
    return asyncio.run(federation_request(destination, "GET", path, **kwargs))


def _replay(request: httpx2.Request) -> httpx2.Response:
    """Reenvia ao nosso servidor exatamente o que o cliente enviou."""
    return client.request(
        request.method,
        request.url.path,
        headers={"Authorization": request.headers["authorization"]},
        content=request.content,
    )


def test_request_is_signed_in_a_way_our_own_server_accepts(wire: Wire) -> None:
    response = _send(SERVER_NAME)

    assert response.status_code == 200
    assert str(wire.sent[0].url) == f"http://{SERVER_NAME}/_federation/v1/ping"
    replayed = _replay(wire.sent[0])
    assert replayed.status_code == 200
    assert replayed.json() == {"origin": SENDER, "server_name": SERVER_NAME}


def test_the_body_is_signed_exactly_as_it_is_sent(wire: Wire) -> None:
    _send(SERVER_NAME, json={"b": 1, "a": "é"})

    sent = wire.sent[0]
    assert sent.content == '{"a":"é","b":1}'.encode()
    assert sent.headers["content-type"] == "application/json"
    assert _replay(sent).status_code == 200

    tampered = client.request(
        "GET",
        "/_federation/v1/ping",
        headers={"Authorization": sent.headers["authorization"]},
        content=b'{"a":"x","b":1}',
    )
    assert tampered.status_code == 401


def test_blocked_destination_is_refused_without_sending_anything(wire: Wire) -> None:
    domain = f"{uuid.uuid4().hex[:8]}.test"
    trust.pin(domain, KEY_ID, "chave")
    FederatedServer.update(trust_status=BLOCKED).where(FederatedServer.domain == domain).execute()

    with pytest.raises(FederationRequestError):
        _send(domain)

    assert wire.sent == []


@pytest.mark.parametrize("destination", [SENDER, "Evil Host/x", "a.test/../b"])
def test_invalid_destination_is_refused(wire: Wire, destination: str) -> None:
    with pytest.raises(FederationRequestError):
        _send(destination)

    assert wire.sent == []


def test_path_must_start_with_a_slash(wire: Wire) -> None:
    with pytest.raises(FederationRequestError):
        _send("outro.test", "_federation/v1/ping")


def test_network_failure_becomes_a_federation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("sem rede", request=request)

    monkeypatch.setattr(discovery, "transport", httpx2.MockTransport(refuse))

    with pytest.raises(FederationRequestError):
        _send("outro.test")
