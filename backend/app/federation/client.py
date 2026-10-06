import time
from typing import Any

import httpx2

from app.core.config import SERVER_NAME
from app.db.sync import run_sync
from app.federation import discovery, trust
from app.federation.keys import KEY_ID, signing_key
from app.federation.signing import authorization_header, canonical_json
from app.models.federated_server import BLOCKED
from app.services.identifiers import DOMAIN_PATTERN

TIMEOUT_SECONDS = 10.0


class FederationRequestError(Exception):
    pass


async def federation_request(
    destination: str, method: str, path: str, json: Any = None
) -> httpx2.Response:
    if DOMAIN_PATTERN.fullmatch(destination) is None or destination == SERVER_NAME:
        raise FederationRequestError(f"destino inválido: {destination!r}")
    if not path.startswith("/"):
        raise FederationRequestError(f"o caminho tem de começar por /: {path!r}")

    server = await run_sync(trust.pinned_server, destination)
    if server is not None and server.trust_status == BLOCKED:
        raise FederationRequestError(f"o servidor {destination} está bloqueado")

    # O corpo serializa-se uma só vez e são esses mesmos bytes que se assinam e
    # enviam: voltar a serializar do outro lado daria bytes diferentes e a
    # assinatura deixaria de bater.
    body = canonical_json(json) if json is not None else b""
    authorization = authorization_header(
        signing_key(), KEY_ID, method, path, SERVER_NAME, destination, int(time.time()), body
    )
    headers = {"Authorization": authorization}
    if json is not None:
        headers["Content-Type"] = "application/json"

    try:
        async with httpx2.AsyncClient(
            transport=discovery.transport,
            timeout=TIMEOUT_SECONDS,
            follow_redirects=False,
        ) as client:
            return await client.request(
                method, f"{discovery.scheme()}://{destination}{path}", headers=headers, content=body
            )
    except httpx2.HTTPError as error:
        raise FederationRequestError(
            f"não foi possível contactar {destination}: {error!r}"
        ) from error
