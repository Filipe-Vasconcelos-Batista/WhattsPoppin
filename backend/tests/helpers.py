"""Helpers partilhados pelos testes de mensagens e da fila offline."""

import base64
import time
import uuid
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

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


def publish_keys(session: dict[str, Any]) -> None:
    response = client.post(
        f"/devices/{session['device_id']}/keys",
        json={
            "client_token": session["token"],
            "identity_key": b64(b"i" * 32),
            "signed_prekey": b64(b"s" * 32),
            "signed_prekey_signature": b64(b"g" * 64),
            "signed_prekey_id": 1,
            "one_time_prekeys": [],
        },
    )
    assert response.status_code == 204


def conversation(a: dict[str, Any], b: dict[str, Any]) -> str:
    response = client.post(
        "/conversations/with", json={"user_id": a["user_id"], "other_user_id": b["user_id"]}
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


# O servidor processa o que recebe pelo socket de forma assíncrona - para
# confirmar um efeito (ex.: ack apagou a linha) espera-se até ele aparecer.
def wait_until(condition: Callable[[], bool], timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.02)
    raise AssertionError("condição não se verificou a tempo")
