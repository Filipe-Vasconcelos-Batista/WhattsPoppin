"""Peewee migrations -- 008_add_federated_servers.py."""


from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    @migrator.create_model
    class FederatedServer(pw.Model):
        domain = pw.CharField(max_length=255, primary_key=True)
        key_id = pw.CharField(max_length=32)
        verify_key = pw.CharField(max_length=64)
        trust_status = pw.CharField(max_length=16)
        first_seen_at = pw.DateTimeField()
        last_seen_at = pw.DateTimeField()
        changed_key = pw.CharField(max_length=64, null=True)
        key_changed_at = pw.DateTimeField(null=True)

        class Meta:
            table_name = "federated_servers"


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    migrator.remove_model('federated_servers')
