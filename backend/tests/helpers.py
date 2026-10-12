"""Helpers partilhados pelos testes de mensagens e da fila offline."""

import base64
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession

from app.main import app

client = TestClient(app)

PASSWORD = "a-long-enough-password"


def b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def register() -> dict[str, Any]:
    username = f"msg-test-{uuid.uuid4().hex[:8]}"
    response = client.post("/auth/register", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    return {**response.json(), "username": username}


def login_new_device(username: str) -> dict[str, Any]:
    response = client.post("/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    session: dict[str, Any] = response.json()
    return session


def auth_headers(session: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['token']}"}


@contextmanager
def connect(ws_client: TestClient, session: dict[str, Any]) -> Iterator[WebSocketTestSession]:
    with ws_client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "auth", "token": session["token"]})
        assert websocket.receive_json() == {"type": "auth_ok"}
        yield websocket


def publish_keys(session: dict[str, Any]) -> None:
    response = client.post(
        f"/devices/{session['device_id']}/keys",
        headers=auth_headers(session),
        json={
            "identity_key": b64(b"i" * 32),
            "signed_prekey": b64(b"s" * 32),
            "signed_prekey_signature": b64(b"g" * 64),
            "signed_prekey_id": 1,
            "one_time_prekeys": [],
        },
    )
    assert response.status_code == 204


def add_contact(session: dict[str, Any], identifier: str) -> dict[str, Any]:
    response = client.post(
        "/contacts", headers=auth_headers(session), json={"identifier": identifier}
    )
    assert response.status_code == 200, response.text
    contact: dict[str, Any] = response.json()
    return contact


def make_contacts(a: dict[str, Any], b: dict[str, Any]) -> None:
    add_contact(a, b["identifier"])
    assert add_contact(b, a["identifier"])["status"] == "accepted"


def conversation(a: dict[str, Any], b: dict[str, Any]) -> str:
    make_contacts(a, b)
    response = client.post(
        "/conversations/with", headers=auth_headers(a), json={"other_user_id": b["user_id"]}
    )
    assert response.status_code == 200
    conversation_id: str = response.json()["conversation_id"]
    return conversation_id


def envelope(device_id: str, n: int) -> dict[str, Any]:
    return {
        "device_id": device_id,
        "header": {"dh": b64(b"d" * 32), "pn": 0, "n": n},
        "ciphertext": b64(f"ciphertext-{n}".encode()),
        "x3dh": None,
    }


def outgoing(
    conversation_id: str, *envelopes: dict[str, Any], client_message_id: str | None = None
) -> dict[str, Any]:
    return {
        "conversation_id": conversation_id,
        "client_message_id": client_message_id or str(uuid.uuid4()),
        "envelopes": list(envelopes),
    }


def wait_until(condition: Callable[[], bool], timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.02)
    raise AssertionError("condição não se verificou a tempo")
