import base64
import os
from functools import cache
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.config import SERVER_SIGNING_KEY_PATH

# Vai no cabeçalho e no .well-known para um dia podermos rodar a chave
# sem que os outros servidores confundam a nova com a antiga.
KEY_ID = "ed25519:1"


class SigningKeyError(Exception):
    pass


def load_or_create_signing_key(path: Path) -> Ed25519PrivateKey:
    if path.exists():
        return _read(path)

    path.parent.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    try:
        # O_EXCL + 0600 na criação: a chave nunca existe com permissões largas, e
        # se dois processos arrancarem juntos só um escreve, o outro lê a dele.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return _read(path)
    with os.fdopen(fd, "wb") as file:
        file.write(pem)
    return key


def _read(path: Path) -> Ed25519PrivateKey:
    try:
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    except (ValueError, TypeError) as error:
        raise SigningKeyError(f"Chave de assinatura inválida em {path}") from error
    if not isinstance(key, Ed25519PrivateKey):
        raise SigningKeyError(f"A chave em {path} não é Ed25519")
    return key


@cache
def signing_key() -> Ed25519PrivateKey:
    return load_or_create_signing_key(SERVER_SIGNING_KEY_PATH)


def public_key_b64(key: Ed25519PrivateKey) -> str:
    raw = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")
