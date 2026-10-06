"""Descoberta da chave de um servidor remoto: GET /.well-known/whattspoppin/server."""

import base64
import binascii
import json
from dataclasses import dataclass
from typing import Any

import httpx2

from app.core.config import FEDERATION_ALLOW_HTTP
from app.services.identifiers import DOMAIN_PATTERN

PROTOCOL_VERSION = "1"
WELL_KNOWN_PATH = "/.well-known/whattspoppin/server"
TIMEOUT_SECONDS = 5.0
MAX_RESPONSE_BYTES = 16 * 1024

# Só os testes mexem nisto, para trocar a rede por um MockTransport.
transport: httpx2.AsyncBaseTransport | None = None


class DiscoveryError(Exception):
    pass


@dataclass(frozen=True)
class ServerKeys:
    server_name: str
    verify_keys: dict[str, str]  # key_id -> chave pública Ed25519 em base64


def scheme() -> str:
    return "http" if FEDERATION_ALLOW_HTTP else "https"


async def fetch_server_keys(domain: str) -> ServerKeys:
    # O domínio vem de um pedido de fora: só se vai buscar o que parece um
    # domínio (com porta opcional), nunca um caminho, utilizador ou query.
    if DOMAIN_PATTERN.fullmatch(domain) is None:
        raise DiscoveryError(f"domínio inválido: {domain!r}")

    url = f"{scheme()}://{domain}{WELL_KNOWN_PATH}"
    try:
        # Sem seguir redirects: um servidor não pode mandar-nos buscar a chave
        # de outro domínio a um sítio que não é o dele.
        async with httpx2.AsyncClient(
            transport=transport, timeout=TIMEOUT_SECONDS, follow_redirects=False
        ) as client, client.stream("GET", url) as response:
            if response.status_code != 200:
                raise DiscoveryError(f"{url} respondeu {response.status_code}")
            body = b""
            async for chunk in response.aiter_bytes():
                body += chunk
                if len(body) > MAX_RESPONSE_BYTES:
                    raise DiscoveryError(f"{url} respondeu com demasiados dados")
    except httpx2.HTTPError as error:
        raise DiscoveryError(f"não foi possível contactar {url}: {error!r}") from error

    return _parse(domain, body)


def _parse(domain: str, body: bytes) -> ServerKeys:
    try:
        data = json.loads(body)
    except ValueError as error:
        raise DiscoveryError("resposta não é JSON") from error

    if not isinstance(data, dict):
        raise DiscoveryError("resposta não é um objeto JSON")
    if data.get("server_name") != domain:
        raise DiscoveryError(f"server_name {data.get('server_name')!r} não é {domain!r}")
    versions = data.get("versions")
    if not isinstance(versions, list) or PROTOCOL_VERSION not in versions:
        raise DiscoveryError(f"o servidor não fala a versão {PROTOCOL_VERSION} do protocolo")

    verify_keys: Any = data.get("verify_keys")
    if not isinstance(verify_keys, dict) or not all(
        isinstance(key_id, str) and _is_ed25519_public_key(key)
        for key_id, key in verify_keys.items()
    ):
        raise DiscoveryError("verify_keys inválido")

    return ServerKeys(server_name=domain, verify_keys=dict(verify_keys))


def _is_ed25519_public_key(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return len(base64.b64decode(value, validate=True)) == 32
    except binascii.Error:
        return False
