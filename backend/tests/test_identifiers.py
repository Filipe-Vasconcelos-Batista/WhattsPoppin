import uuid

import pytest

from app.services.identifiers import (
    IdentifierError,
    format_identifier,
    is_local,
    parse_identifier,
)
from tests.helpers import PASSWORD, client, register


def test_local_users_get_the_server_name_as_domain() -> None:
    assert format_identifier("alice", None) == "alice@test.local"
    assert format_identifier("bob", "casa.pt") == "bob@casa.pt"


def test_is_local() -> None:
    assert is_local(None)
    assert is_local("test.local")
    assert not is_local("casa.pt")


@pytest.mark.parametrize(
    ("identifier", "expected"),
    [
        ("alice@casa.pt", ("alice", "casa.pt")),
        ("bob.silva@localhost:8002", ("bob.silva", "localhost:8002")),
        ("a_b-c@sub.domain.example", ("a_b-c", "sub.domain.example")),
    ],
)
def test_parse_identifier(identifier: str, expected: tuple[str, str]) -> None:
    assert parse_identifier(identifier) == expected


@pytest.mark.parametrize(
    "identifier",
    ["alice", "alice@", "@casa.pt", "a@b@c", "Alice@casa.pt", "al@casa.pt", "alice@casa pt"],
)
def test_parse_identifier_rejects_invalid(identifier: str) -> None:
    with pytest.raises(IdentifierError):
        parse_identifier(identifier)


def test_register_returns_the_full_identifier() -> None:
    alice = register()

    assert alice["identifier"] == f"{alice['username']}@test.local"
    bob = register()
    other = next(
        user
        for user in client.post(
            "/auth/login", json={"username": bob["username"], "password": PASSWORD}
        ).json()["other_users"]
        if user["user_id"] == alice["user_id"]
    )
    assert other["identifier"] == alice["identifier"]


def test_username_is_lowercased_on_register_and_login() -> None:
    username = f"Mixed-{uuid.uuid4().hex[:8]}"

    registered = client.post("/auth/register", json={"username": username, "password": PASSWORD})
    login = client.post("/auth/login", json={"username": username.upper(), "password": PASSWORD})

    assert registered.status_code == 200
    assert registered.json()["identifier"] == f"{username.lower()}@test.local"
    assert login.status_code == 200
    assert login.json()["user_id"] == registered.json()["user_id"]


def test_same_username_with_different_case_is_taken() -> None:
    username = f"taken-{uuid.uuid4().hex[:8]}"
    client.post("/auth/register", json={"username": username, "password": PASSWORD})

    response = client.post(
        "/auth/register", json={"username": username.upper(), "password": PASSWORD}
    )

    assert response.status_code == 400


@pytest.mark.parametrize("username", ["ab", "a" * 33, "alice@casa.pt", "com espaço", "ação"])
def test_register_rejects_invalid_usernames(username: str) -> None:
    response = client.post("/auth/register", json={"username": username, "password": PASSWORD})

    assert response.status_code == 400
