import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.federation.keys import KEY_ID, public_key_b64
from app.federation.signing import (
    SignatureHeaderError,
    authorization_header,
    canonical_json,
    parse_authorization,
    sign,
    signing_payload,
    verify,
)


def _header(key: Ed25519PrivateKey, body: bytes = b"", ts: int = 1_700_000_000) -> str:
    return authorization_header(
        key, KEY_ID, "GET", "/_federation/v1/ping", "a.test", "b.test", ts, body
    )


def test_canonical_json_ignores_key_order_and_whitespace() -> None:
    assert canonical_json({"b": 1, "a": [1, 2]}) == b'{"a":[1,2],"b":1}'
    assert canonical_json({"a": [1, 2], "b": 1}) == canonical_json({"b": 1, "a": [1, 2]})


def test_canonical_json_keeps_unicode_as_utf8() -> None:
    assert canonical_json({"nome": "João"}) == '{"nome":"João"}'.encode()


def test_signing_payload_has_the_fields_the_protocol_signs() -> None:
    payload = signing_payload("get", "/x?y=1", "a.test", "b.test", 42, b"corpo")
    assert json.loads(payload) == {
        "method": "GET",
        "uri": "/x?y=1",
        "origin": "a.test",
        "destination": "b.test",
        "ts": 42,
        "content_sha256": hashlib.sha256(b"corpo").hexdigest(),
    }


def test_sign_and_verify() -> None:
    key = Ed25519PrivateKey.generate()
    payload = b"qualquer coisa"
    assert verify(public_key_b64(key), payload, sign(key, payload))


def test_verify_rejects_other_key_and_altered_payload() -> None:
    key = Ed25519PrivateKey.generate()
    sig = sign(key, b"original")
    assert not verify(public_key_b64(key), b"adulterado", sig)
    assert not verify(public_key_b64(Ed25519PrivateKey.generate()), b"original", sig)


@pytest.mark.parametrize("bad", ["", "não é base64!", "AAAA"])
def test_verify_returns_false_for_malformed_input(bad: str) -> None:
    key = Ed25519PrivateKey.generate()
    good_sig = sign(key, b"x")
    assert not verify(bad, b"x", good_sig)
    assert not verify(public_key_b64(key), b"x", bad)


def test_header_round_trip() -> None:
    key = Ed25519PrivateKey.generate()
    parsed = parse_authorization(_header(key, ts=123))

    assert (parsed.origin, parsed.destination, parsed.key_id, parsed.ts) == (
        "a.test",
        "b.test",
        KEY_ID,
        123,
    )
    payload = signing_payload("GET", "/_federation/v1/ping", "a.test", "b.test", 123, b"")
    assert verify(public_key_b64(key), payload, parsed.sig)


def test_header_signature_covers_the_body() -> None:
    key = Ed25519PrivateKey.generate()
    parsed = parse_authorization(_header(key, body=b'{"a":1}', ts=1))
    other_body = signing_payload("GET", "/_federation/v1/ping", "a.test", "b.test", 1, b'{"a":2}')
    assert not verify(public_key_b64(key), other_body, parsed.sig)


def test_header_with_localhost_port_in_origin() -> None:
    key = Ed25519PrivateKey.generate()
    header = authorization_header(
        key, KEY_ID, "GET", "/x", "localhost:8001", "localhost:8002", 1, b""
    )
    assert parse_authorization(header).origin == "localhost:8001"


_SIG = base64.b64encode(b"x" * 64).decode()
_VALID = f'WP-Sig origin="a",destination="b",key="ed25519:1",ts="1",sig="{_SIG}"'


@pytest.mark.parametrize(
    "header",
    [
        "",
        "Bearer abc",
        "WP-Sig",
        "WP-Sig ",
        _VALID.replace("WP-Sig", "wp-sig"),
        _VALID.replace('origin="a"', "origin=a"),  # sem aspas
        _VALID.replace('origin="a",', ""),  # campo em falta
        _VALID + ',origin="c"',  # campo repetido
        _VALID + ',extra="1"',  # campo desconhecido
        _VALID.replace('ts="1"', 'ts="abc"'),
        _VALID.replace('ts="1"', 'ts="-1"'),
        _VALID.replace('ts="1"', 'ts="1.5"'),
        _VALID.replace('ts="1"', 'ts=""'),
        _VALID.replace(",", ", "),  # espaços a mais
    ],
)
def test_parse_authorization_rejects_invalid_headers(header: str) -> None:
    with pytest.raises(SignatureHeaderError):
        parse_authorization(header)


def test_parse_authorization_accepts_the_reference_header() -> None:
    assert parse_authorization(_VALID).ts == 1
