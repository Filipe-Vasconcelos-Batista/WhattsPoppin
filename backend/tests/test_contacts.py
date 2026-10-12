from typing import Any

from fastapi.testclient import TestClient

from tests.helpers import (
    add_contact,
    auth_headers,
    client,
    connect,
    make_contacts,
    register,
)


def _contacts(session: dict[str, Any]) -> dict[str, str]:
    response = client.get("/contacts", headers=auth_headers(session))
    assert response.status_code == 200
    return {contact["user_id"]: contact["status"] for contact in response.json()}


def _accept(session: dict[str, Any], user_id: str) -> Any:
    return client.post(f"/contacts/{user_id}/accept", headers=auth_headers(session))


def _remove(session: dict[str, Any], user_id: str) -> Any:
    return client.delete(f"/contacts/{user_id}", headers=auth_headers(session))


def _open_conversation(a: dict[str, Any], b: dict[str, Any]) -> Any:
    return client.post(
        "/conversations/with", headers=auth_headers(a), json={"other_user_id": b["user_id"]}
    )


def test_request_creates_both_pending_sides() -> None:
    alice = register()
    bob = register()

    contact = add_contact(alice, bob["identifier"])

    assert contact["status"] == "pending_outgoing"
    assert contact["identifier"] == bob["identifier"]
    assert _contacts(alice) == {bob["user_id"]: "pending_outgoing"}
    assert _contacts(bob) == {alice["user_id"]: "pending_incoming"}


def test_bare_username_means_a_local_account() -> None:
    alice = register()
    bob = register()

    assert add_contact(alice, bob["username"])["user_id"] == bob["user_id"]


def test_accepting_makes_both_sides_accepted() -> None:
    alice = register()
    bob = register()
    add_contact(alice, bob["identifier"])

    response = _accept(bob, alice["user_id"])

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert _contacts(alice) == {bob["user_id"]: "accepted"}
    assert _contacts(bob) == {alice["user_id"]: "accepted"}


def test_requesting_someone_who_already_asked_accepts() -> None:
    alice = register()
    bob = register()
    add_contact(alice, bob["identifier"])

    assert add_contact(bob, alice["identifier"])["status"] == "accepted"
    assert _contacts(alice) == {bob["user_id"]: "accepted"}


def test_requesting_twice_changes_nothing() -> None:
    alice = register()
    bob = register()
    add_contact(alice, bob["identifier"])

    assert add_contact(alice, bob["identifier"])["status"] == "pending_outgoing"
    assert _contacts(bob) == {alice["user_id"]: "pending_incoming"}


def test_only_incoming_requests_can_be_accepted() -> None:
    alice = register()
    bob = register()
    add_contact(alice, bob["identifier"])

    assert _accept(alice, bob["user_id"]).status_code == 404


def test_declining_is_not_revealed_to_the_requester() -> None:
    alice = register()
    bob = register()
    add_contact(alice, bob["identifier"])

    assert _remove(bob, alice["user_id"]).status_code == 204

    assert _contacts(bob) == {}
    assert _contacts(alice) == {bob["user_id"]: "pending_outgoing"}
    assert _open_conversation(alice, bob).status_code == 403


def test_adding_after_declining_accepts_the_old_request() -> None:
    alice = register()
    bob = register()
    add_contact(alice, bob["identifier"])
    _remove(bob, alice["user_id"])

    assert add_contact(bob, alice["identifier"])["status"] == "accepted"
    assert _contacts(alice) == {bob["user_id"]: "accepted"}


def test_cancelling_a_request_removes_it_from_both_sides() -> None:
    alice = register()
    bob = register()
    add_contact(alice, bob["identifier"])

    assert _remove(alice, bob["user_id"]).status_code == 204

    assert _contacts(alice) == {}
    assert _contacts(bob) == {}


def test_removing_a_contact_blocks_new_messages() -> None:
    alice = register()
    bob = register()
    make_contacts(alice, bob)
    assert _open_conversation(alice, bob).status_code == 200

    assert _remove(bob, alice["user_id"]).status_code == 204

    assert _contacts(alice) == {bob["user_id"]: "pending_outgoing"}
    assert _open_conversation(alice, bob).status_code == 403
    assert _open_conversation(bob, alice).status_code == 403


def test_removing_an_unknown_contact_is_not_found() -> None:
    alice = register()
    bob = register()

    assert _remove(alice, bob["user_id"]).status_code == 404


def test_cannot_add_yourself() -> None:
    alice = register()

    response = client.post(
        "/contacts", headers=auth_headers(alice), json={"identifier": alice["identifier"]}
    )

    assert response.status_code == 400


def test_invalid_and_unknown_identifiers() -> None:
    alice = register()

    invalid = client.post(
        "/contacts", headers=auth_headers(alice), json={"identifier": "no spaces@x"}
    )
    unknown = client.post(
        "/contacts", headers=auth_headers(alice), json={"identifier": "ninguem-aqui@test.local"}
    )

    assert invalid.status_code == 400
    assert unknown.status_code == 404


def test_conversation_needs_an_accepted_contact() -> None:
    alice = register()
    bob = register()
    add_contact(alice, bob["identifier"])

    assert _open_conversation(alice, bob).status_code == 403

    _accept(bob, alice["user_id"])

    assert _open_conversation(alice, bob).status_code == 200


def test_session_carries_pending_requests() -> None:
    alice = register()
    bob = register()
    add_contact(alice, bob["identifier"])

    session = client.post("/auth/session", headers=auth_headers(bob)).json()

    assert session["other_users"] == []
    assert [(c["user_id"], c["status"]) for c in session["contact_requests"]] == [
        (alice["user_id"], "pending_incoming")
    ]


def test_both_sides_are_told_over_the_socket(ws_client: TestClient) -> None:
    alice = register()
    bob = register()

    with connect(ws_client, bob) as bob_ws:
        ws_client.post(
            "/contacts", headers=auth_headers(alice), json={"identifier": bob["identifier"]}
        )
        request_event = bob_ws.receive_json()

    with connect(ws_client, alice) as alice_ws:
        ws_client.post(f"/contacts/{alice['user_id']}/accept", headers=auth_headers(bob))
        accept_event = alice_ws.receive_json()

    assert request_event["type"] == "contact_updated"
    assert request_event["contact"]["user_id"] == alice["user_id"]
    assert request_event["contact"]["status"] == "pending_incoming"
    assert accept_event["type"] == "contact_updated"
    assert accept_event["contact"]["user_id"] == bob["user_id"]
    assert accept_event["contact"]["status"] == "accepted"


def test_cancelled_request_disappears_over_the_socket(ws_client: TestClient) -> None:
    alice = register()
    bob = register()
    add_contact(alice, bob["identifier"])

    with connect(ws_client, bob) as bob_ws:
        ws_client.delete(f"/contacts/{bob['user_id']}", headers=auth_headers(alice))
        event = bob_ws.receive_json()

    assert event == {"type": "contact_removed", "user_id": alice["user_id"]}
