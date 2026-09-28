import re

from app.core.config import SERVER_NAME

USERNAME_PATTERN = re.compile(r"[a-z0-9._-]{3,32}")
DOMAIN_PATTERN = re.compile(r"[a-z0-9.-]+(:[0-9]{1,5})?")


class IdentifierError(ValueError):
    pass


def normalize_username(username: str) -> str:
    return username.strip().lower()


def is_valid_username(username: str) -> bool:
    return USERNAME_PATTERN.fullmatch(username) is not None


def is_local(domain: str | None) -> bool:
    return domain is None or domain == SERVER_NAME


# domain None = conta deste servidor (ver User.domain)
def format_identifier(username: str, domain: str | None) -> str:
    return f"{username}@{domain or SERVER_NAME}"


def parse_identifier(identifier: str) -> tuple[str, str]:
    username, separator, domain = identifier.partition("@")
    if not separator or not is_valid_username(username) or not DOMAIN_PATTERN.fullmatch(domain):
        raise IdentifierError(f"Identificador inválido: {identifier!r}")
    return username, domain
