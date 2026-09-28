from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    migrator.add_fields(
        'devices',

        token_hash=pw.CharField(max_length=64, null=True, unique=True))

    # Igual a hashlib.sha256(token.encode()).hexdigest() em app/services/auth.py
    migrator.sql(
        "UPDATE devices SET token_hash = encode(sha256(convert_to(client_token, 'UTF8')), 'hex') "
        "WHERE client_token IS NOT NULL"
    )

    migrator.remove_fields('devices', 'client_token')


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    migrator.add_fields(
        'devices',

        client_token=pw.CharField(max_length=64, null=True, unique=True))

    migrator.remove_fields('devices', 'token_hash')
