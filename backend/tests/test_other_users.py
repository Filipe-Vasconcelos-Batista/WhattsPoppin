from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core import config
from tests.helpers import auth_headers, client, connect, conversation, make_contacts, register


def _session(session: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/auth/session", headers=auth_headers(session))
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


def _other_user(session: dict[str, Any], user_id: str) -> dict[str, Any]:
    other_user: dict[str, Any] = next(
        user for user in _session(session)["other_users"] if user["user_id"] == user_id
    )
    return other_user


def _ids(users: list[dict[str, Any]]) -> set[str]:
    return {user["user_id"] for user in users}


@pytest.fixture
def directory_mode(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(config, "SERVER_MODE", config.SERVER_MODE_DIRECTORY)
    yield


def test_contacts_have_no_conversation_until_one_is_opened() -> None:
    alice = register()
    bob = register()
    make_contacts(alice, bob)

    assert _other_user(alice, bob["user_id"])["conversation_id"] is None

    conversation_id = conversation(alice, bob)

    assert _other_user(alice, bob["user_id"])["conversation_id"] == conversation_id
    assert _other_user(bob, alice["user_id"])["conversation_id"] == conversation_id


def test_conversation_id_is_per_pair() -> None:
    alice = register()
    bob = register()
    carol = register()
    conversation(alice, bob)
    make_contacts(alice, carol)
    make_contacts(carol, bob)

    assert _other_user(alice, carol["user_id"])["conversation_id"] is None
    assert _other_user(carol, bob["user_id"])["conversation_id"] is None


def test_private_mode_lists_only_accepted_contacts() -> None:
    alice = register()
    bob = register()
    carol = register()
    make_contacts(alice, bob)

    session = _session(alice)

    assert _ids(session["other_users"]) == {bob["user_id"]}
    assert session["contact_requests"] == []
    assert _session(carol)["other_users"] == []


def test_directory_mode_lists_every_local_member(directory_mode: None) -> None:
    alice = register()
    bob = register()

    session = _session(alice)

    assert bob["user_id"] in _ids(session["other_users"])
    assert alice["user_id"] not in _ids(session["other_users"])
    assert session["contact_requests"] == []


def test_directory_mode_allows_conversations_without_contacts(directory_mode: None) -> None:
    alice = register()
    bob = register()

    response = client.post(
        "/conversations/with", headers=auth_headers(alice), json={"other_user_id": bob["user_id"]}
    )

    assert response.status_code == 200


def test_new_users_are_announced_only_in_directory_mode(
    ws_client: TestClient, directory_mode: None
) -> None:
    alice = register()

    with connect(ws_client, alice) as alice_ws:
        response = ws_client.post(
            "/auth/register", json={"username": "dir-" + alice["username"], "password": "x" * 12}
        )
        event = alice_ws.receive_json()

    assert event["type"] == "user_registered"
    assert event["user"]["user_id"] == response.json()["user_id"]
