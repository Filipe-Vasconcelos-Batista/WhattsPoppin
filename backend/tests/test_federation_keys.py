import stat
from pathlib import Path

import pytest

from app.federation.keys import SigningKeyError, load_or_create_signing_key, public_key_b64


def test_first_call_creates_the_key_file_readable_only_by_the_owner(tmp_path: Path) -> None:
    path = tmp_path / "nova" / "pasta" / "signing.key"

    load_or_create_signing_key(path)

    assert path.exists()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_second_call_reuses_the_same_key(tmp_path: Path) -> None:
    path = tmp_path / "signing.key"

    first = load_or_create_signing_key(path)
    second = load_or_create_signing_key(path)

    assert public_key_b64(first) == public_key_b64(second)


def test_different_files_give_different_keys(tmp_path: Path) -> None:
    a = load_or_create_signing_key(tmp_path / "a.key")
    b = load_or_create_signing_key(tmp_path / "b.key")

    assert public_key_b64(a) != public_key_b64(b)


def test_invalid_file_fails_instead_of_being_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "signing.key"
    path.write_text("isto não é uma chave")

    with pytest.raises(SigningKeyError):
        load_or_create_signing_key(path)

    assert path.read_text() == "isto não é uma chave"


def test_key_of_another_type_is_refused(tmp_path: Path) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed448 import Ed448PrivateKey

    path = tmp_path / "ed448.key"
    path.write_bytes(
        Ed448PrivateKey.generate().private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )

    with pytest.raises(SigningKeyError):
        load_or_create_signing_key(path)


def test_public_key_is_32_bytes_in_base64(tmp_path: Path) -> None:
    import base64

    key = load_or_create_signing_key(tmp_path / "signing.key")

    assert len(base64.b64decode(public_key_b64(key))) == 32
