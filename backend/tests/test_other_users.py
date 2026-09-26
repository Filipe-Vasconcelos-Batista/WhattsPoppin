from typing import Any

from tests.helpers import client, conversation, register


def _other_user(session: dict[str, Any], user_id: str) -> dict[str, Any]:
    response = client.post("/auth/session", json={"token": session["token"]})
    assert response.status_code == 200
    other_user: dict[str, Any] = next(
        user for user in response.json()["other_users"] if user["user_id"] == user_id
    )
    return other_user


def test_other_users_have_no_conversation_until_one_is_opened() -> None:
    alice = register()
    bob = register()

    assert _other_user(alice, bob["user_id"])["conversation_id"] is None

    conversation_id = conversation(alice, bob)

    assert _other_user(alice, bob["user_id"])["conversation_id"] == conversation_id
    # Quem não abriu a conversa também a vê - foi o outro lado que a criou.
    assert _other_user(bob, alice["user_id"])["conversation_id"] == conversation_id


def test_conversation_id_is_per_pair() -> None:
    alice = register()
    bob = register()
    carol = register()
    conversation(alice, bob)

    assert _other_user(alice, carol["user_id"])["conversation_id"] is None
    assert _other_user(carol, bob["user_id"])["conversation_id"] is None
