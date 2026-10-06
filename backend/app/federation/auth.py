"""Autenticação dos pedidos que chegam de outros servidores (cabeçalho WP-Sig)."""

import logging
import time
from typing import NoReturn

from fastapi import HTTPException, Request

from app.core.config import SERVER_NAME
from app.db.sync import run_sync
from app.federation import trust
from app.federation.discovery import DiscoveryError, ServerKeys, fetch_server_keys
from app.federation.signing import (
    SignatureHeaderError,
    SignedHeader,
    parse_authorization,
    signing_payload,
    verify,
)
from app.models.federated_server import BLOCKED
from app.services.identifiers import DOMAIN_PATTERN

logger = logging.getLogger(__name__)

MAX_CLOCK_SKEW_SECONDS = 300


def _reject(status: int, reason: str, origin: str | None = None) -> NoReturn:
    logger.warning("pedido federado recusado (origem %r): %s", origin, reason)
    raise HTTPException(status_code=status, detail="Pedido federado recusado")


async def federation_origin(request: Request) -> str:
    """Devolve o domínio do servidor que enviou o pedido, já verificado."""
    body = await request.body()
    try:
        header = parse_authorization(request.headers.get("authorization", ""))
    except SignatureHeaderError as error:
        _reject(401, f"cabeçalho inválido: {error}")

    origin = header.origin
    if header.destination != SERVER_NAME:
        _reject(401, f"o destino é {header.destination!r} e não este servidor", origin)
    if origin == SERVER_NAME:
        _reject(401, "a origem é este próprio servidor", origin)
    if DOMAIN_PATTERN.fullmatch(origin) is None:
        _reject(401, "a origem não é um domínio válido", origin)
    if abs(time.time() - header.ts) > MAX_CLOCK_SKEW_SECONDS:
        _reject(401, "ts fora da janela permitida", origin)

    uri = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    payload = signing_payload(request.method, uri, origin, header.destination, header.ts, body)

    server = await run_sync(trust.pinned_server, origin)
    if server is None:
        await _accept_new_server(header, payload)
    else:
        if server.trust_status == BLOCKED:
            _reject(403, "servidor bloqueado", origin)
        await _check_known_server(header, payload, server.key_id, server.verify_key)

    await run_sync(trust.touch, origin)
    return origin


async def _accept_new_server(header: SignedHeader, payload: bytes) -> None:
    origin = header.origin
    keys = await _discover(origin)
    key = keys.verify_keys.get(header.key_id)
    if key is None or not verify(key, payload, header.sig):
        _reject(401, "assinatura não verifica com a chave publicada pelo servidor", origin)

    # TOFU: é a partir daqui que esta chave passa a ser a do servidor. Se outro
    # pedido o fixou primeiro, vale a chave que ficou na BD.
    pinned = await run_sync(trust.pin, origin, header.key_id, key)
    if pinned.trust_status == BLOCKED:
        _reject(403, "servidor bloqueado", origin)
    if pinned.key_id != header.key_id or pinned.verify_key != key:
        _reject(401, "outra chave foi fixada em simultâneo", origin)


async def _check_known_server(
    header: SignedHeader, payload: bytes, pinned_key_id: str, pinned_key: str
) -> None:
    origin = header.origin
    if header.key_id == pinned_key_id and verify(pinned_key, payload, header.sig):
        return

    # Assinatura recusada: pode ser um pedido forjado ou o servidor ter mudado
    # de chave. Vai-se ver o que ele publica agora - se for outra chave, fica
    # registado para um admin decidir, mas este pedido é recusado na mesma.
    keys = await _discover(origin)
    published = keys.verify_keys.get(pinned_key_id)
    if published is not None and published != pinned_key:
        logger.warning(
            "o servidor %r publica uma chave diferente da fixada - recusado e marcado", origin
        )
        await run_sync(trust.mark_key_changed, origin, published)
    _reject(401, "assinatura não verifica com a chave fixada", origin)


async def _discover(origin: str) -> ServerKeys:
    try:
        return await fetch_server_keys(origin)
    except DiscoveryError as error:
        _reject(401, f"não foi possível obter a chave: {error}", origin)
