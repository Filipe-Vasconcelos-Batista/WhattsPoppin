import asyncio
import sys

from app.federation.client import FederationRequestError, federation_request


async def main(destination: str) -> int:
    try:
        response = await federation_request(destination, "GET", "/_federation/v1/ping")
    except FederationRequestError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1

    print(f"{response.status_code} {response.text}")
    return 0 if response.is_success else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("uso: python -m app.federation.ping <domínio[:porta]>")
    sys.exit(asyncio.run(main(sys.argv[1])))
