"""Confiança nas chaves dos servidores remotos (TOFU) sobre `federated_servers`.
Síncrono, como o resto do acesso à BD: quem chama de código async usa `run_sync`."""

from datetime import UTC, datetime

from app.models import FederatedServer


def pinned_server(domain: str) -> FederatedServer | None:
    return FederatedServer.get_or_none(FederatedServer.domain == domain)


# Se dois primeiros pedidos do mesmo servidor chegarem em simultâneo, só o
# primeiro insert fica; devolve-se a linha que ficou na BD (e não a chave
# recebida) para quem chama poder detetar que o vencedor fixou outra chave.
def pin(domain: str, key_id: str, verify_key: str) -> FederatedServer:
    FederatedServer.insert(
        domain=domain, key_id=key_id, verify_key=verify_key
    ).on_conflict_ignore().execute()
    return FederatedServer.get(FederatedServer.domain == domain)


def mark_key_changed(domain: str, new_key: str) -> None:
    FederatedServer.update(changed_key=new_key, key_changed_at=datetime.now(UTC)).where(
        FederatedServer.domain == domain
    ).execute()


def touch(domain: str) -> None:
    FederatedServer.update(last_seen_at=datetime.now(UTC)).where(
        FederatedServer.domain == domain
    ).execute()
