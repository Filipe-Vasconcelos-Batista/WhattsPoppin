import asyncio
import sys

from app.federation.client import FederationRequestError, federation_request

USAGE = "uso: python -m app.federation.ping <domínio[:porta]> [MÉTODO CAMINHO]"


async def main(destination: str, method: str, path: str) -> int:
    try:
        response = await federation_request(destination, method, path)
    except FederationRequestError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1

    print(f"{response.status_code} {response.text}")
    return 0 if response.is_success else 1


if __name__ == "__main__":
    match sys.argv[1:]:
        case [destination]:
            sys.exit(asyncio.run(main(destination, "GET", "/_federation/v1/ping")))
        case [destination, method, path]:
            sys.exit(asyncio.run(main(destination, method.upper(), path)))
        case _:
            sys.exit(USAGE)
