from typing import Any

from fastapi.testclient import TestClient

from tests.helpers import PASSWORD, client, register


def _update(session: dict[str, Any], display_name: str, http: TestClient = client) -> Any:
    return http.patch(
        "/users/me/display_name",
        json={"token": session["token"], "display_name": display_name},
    )


def test_update_display_name_is_trimmed_and_persisted() -> None:
    alice = register()
    bob = register()

    response = _update(alice, "  Alice Silva  ")

    assert response.status_code == 200
    assert response.json() == {"display_name": "Alice Silva"}
    login = client.post("/auth/login", json={"username": alice["username"], "password": PASSWORD})
    assert login.json()["display_name"] == "Alice Silva"
    session = client.post("/auth/session", json={"token": bob["token"]}).json()
    alice_seen_by_bob = next(
        user for user in session["other_users"] if user["user_id"] == alice["user_id"]
    )
    assert alice_seen_by_bob["display_name"] == "Alice Silva"


def test_update_display_name_rejects_invalid_token() -> None:
    response = _update({"token": "not-a-real-token"}, "Alguém")

    assert response.status_code == 401


def test_update_display_name_rejects_empty_or_too_long() -> None:
    alice = register()

    assert _update(alice, "   ").status_code == 400
    assert _update(alice, "a" * 81).status_code == 400
    assert _update(alice, "a" * 80).status_code == 200


def test_other_connected_devices_are_told_about_the_new_name(ws_client: TestClient) -> None:
    alice = register()
    bob = register()

    with ws_client.websocket_connect(f"/ws?device_id={bob['device_id']}") as bob_ws:
        assert _update(alice, "Alice Nova", http=ws_client).status_code == 200
        event = bob_ws.receive_json()

    assert event == {
        "type": "user_updated",
        "user": {"user_id": alice["user_id"], "display_name": "Alice Nova"},
    }
