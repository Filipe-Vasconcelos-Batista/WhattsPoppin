"""Peewee migrations -- 007_add_user_domain.py.
"""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    migrator.add_fields(
        'users',

        domain=pw.CharField(max_length=255, null=True))

    migrator.drop_index('users', 'username')
    migrator.sql(
        "CREATE UNIQUE INDEX users_local_username ON users (username) WHERE domain IS NULL"
    )
    migrator.sql(
        "CREATE UNIQUE INDEX users_remote_username_domain ON users (username, domain) "
        "WHERE domain IS NOT NULL"
    )


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    migrator.sql("DROP INDEX users_remote_username_domain")
    migrator.sql("DROP INDEX users_local_username")
    migrator.add_index('users', 'username', unique=True)
    migrator.remove_fields('users', 'domain')
