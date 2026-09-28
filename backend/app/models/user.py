import uuid
from datetime import UTC, datetime

import peewee as pw

from app.models.base import BaseModel


class User(BaseModel):
    id = pw.UUIDField(primary_key=True, default=uuid.uuid4)
    # Único por domínio - índices parciais na migração 007, porque o Postgres
    # trata cada NULL como diferente e um UNIQUE(username, domain) deixaria
    # passar dois locais com o mesmo username.
    username = pw.CharField(max_length=32)
    # NULL = conta deste servidor. Só os utilizadores-sombra de outros
    # servidores têm domínio, e mudar o SERVER_NAME não obriga a reescrever
    # as contas locais.
    domain = pw.CharField(max_length=255, null=True)
    password_hash = pw.CharField(max_length=100)
    display_name = pw.CharField(max_length=80)
    created_at = pw.DateTimeField(default=lambda: datetime.now(UTC))

    class Meta:
        table_name = "users"
