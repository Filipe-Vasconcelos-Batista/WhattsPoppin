"""Peewee migrations -- 005_add_pending_messages.py.

Fila offline: envelopes cifrados à espera do ack de cada device destinatário.
"""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    @migrator.create_model
    class PendingMessage(pw.Model):
        id = pw.UUIDField(primary_key=True)
        recipient_device = pw.ForeignKeyField(column_name='recipient_device_id', field='id', model=migrator.orm['devices'], on_delete='CASCADE')
        payload = pw.TextField()
        created_at = pw.DateTimeField(index=True)

        class Meta:
            table_name = "pending_messages"
            indexes = ((("recipient_device", "created_at"), False),)


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    migrator.remove_model('pending_messages')
