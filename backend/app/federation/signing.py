"""Assinatura e verificação de pedidos entre servidores. Funções puras: sem BD
nem rede, para se poderem testar (e rever) isoladas."""

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

SCHEME = "WP-Sig"
FIELDS = ("origin", "destination", "key", "ts", "sig")

_FIELD = r'[a-z]+="[^"]*"'
_HEADER_PATTERN = re.compile(rf"{SCHEME} {_FIELD}(,{_FIELD})*")


class SignatureHeaderError(ValueError):
    pass


@dataclass(frozen=True)
class SignedHeader:
    origin: str
    destination: str
    key_id: str
    ts: int
    sig: str


# O que se assina tem de ser byte a byte igual nos dois lados, por isso a
# ordem das chaves e os espaços ficam fixos.
def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def signing_payload(
    method: str, uri: str, origin: str, destination: str, ts: int, body: bytes
) -> bytes:
    # Entram o destino e o URI para um pedido capturado não servir noutro
    # servidor nem noutro endpoint, e o hash do corpo para não o poderem trocar.
    return canonical_json(
        {
            "method": method.upper(),
            "uri": uri,
            "origin": origin,
            "destination": destination,
            "ts": ts,
            "content_sha256": hashlib.sha256(body).hexdigest(),
        }
    )


def sign(key: Ed25519PrivateKey, payload: bytes) -> str:
    return base64.b64encode(key.sign(payload)).decode("ascii")


def authorization_header(
    key: Ed25519PrivateKey,
    key_id: str,
    method: str,
    uri: str,
    origin: str,
    destination: str,
    ts: int,
    body: bytes,
) -> str:
    sig = sign(key, signing_payload(method, uri, origin, destination, ts, body))
    return (
        f'{SCHEME} origin="{origin}",destination="{destination}",'
        f'key="{key_id}",ts="{ts}",sig="{sig}"'
    )


def parse_authorization(header: str) -> SignedHeader:
    if _HEADER_PATTERN.fullmatch(header) is None:
        raise SignatureHeaderError("formato inválido")

    fields: dict[str, str] = {}
    for part in header.removeprefix(f"{SCHEME} ").split(","):
        name, _, quoted = part.partition("=")
        if name in fields:
            raise SignatureHeaderError(f"campo repetido: {name}")
        fields[name] = quoted[1:-1]

    unknown = fields.keys() - set(FIELDS)
    missing = set(FIELDS) - fields.keys()
    if unknown or missing:
        raise SignatureHeaderError(
            f"campos inesperados {sorted(unknown)} ou em falta {sorted(missing)}"
        )
    if not fields["ts"].isascii() or not fields["ts"].isdigit():
        raise SignatureHeaderError("ts inválido")

    return SignedHeader(
        origin=fields["origin"],
        destination=fields["destination"],
        key_id=fields["key"],
        ts=int(fields["ts"]),
        sig=fields["sig"],
    )


# Qualquer coisa mal formada (chave, assinatura, base64) é simplesmente "não
# verifica": quem chama só precisa de saber sim ou não.
def verify(public_key_b64: str, payload: bytes, sig_b64: str) -> bool:
    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(public_key_b64, validate=True)
        )
        public_key.verify(base64.b64decode(sig_b64, validate=True), payload)
    except (InvalidSignature, ValueError, binascii.Error):
        return False
    return True
