"""Peewee migrations -- 004_add_e2e_keys.py.

Some examples (model - class or model name)::

    > Model = migrator.orm['table_name']            # Return model in current state by name
    > Model = migrator.ModelClass                   # Return model in current state by name

    > migrator.sql(sql)                             # Run custom SQL
    > migrator.run(func, *args, **kwargs)           # Run python function with the given args
    > migrator.create_model(Model)                  # Create a model (could be used as decorator)
    > migrator.remove_model(model, cascade=True)    # Remove a model
    > migrator.add_fields(model, **fields)          # Add fields (allow_not_null=True skips default)
    > migrator.change_fields(model, **fields)       # Change fields
    > migrator.remove_fields(model, *field_names, cascade=True)
    > migrator.rename_field(model, old_field_name, new_field_name)
    > migrator.rename_table(model, new_table_name)
    > migrator.add_index(model, *col_names, unique=False)
    > migrator.add_not_null(model, *field_names)
    > migrator.add_default(model, field_name, default)
    > migrator.add_constraint(model, name, sql)
    > migrator.drop_index(model, *col_names)
    > migrator.drop_not_null(model, *field_names)
    > migrator.drop_constraints(model, *constraints)

"""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    migrator.add_fields(
        'devices',

        identity_key=pw.BlobField(null=True),
        signed_prekey=pw.BlobField(null=True),
        signed_prekey_signature=pw.BlobField(null=True),
        signed_prekey_id=pw.IntegerField(null=True))

    @migrator.create_model
    class OneTimePrekey(pw.Model):
        id = pw.UUIDField(primary_key=True)
        device = pw.ForeignKeyField(column_name='device_id', field='id', model=migrator.orm['devices'], on_delete='CASCADE')
        key_id = pw.IntegerField()
        public_key = pw.BlobField()

        class Meta:
            table_name = "one_time_prekeys"

    migrator.remove_fields('users', 'identity_public_key')


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    migrator.add_fields(
        'users',
        allow_not_null=True,

        identity_public_key=pw.BlobField())

    migrator.remove_model('one_time_prekeys')

    migrator.remove_fields(
        'devices',
        'identity_key', 'signed_prekey', 'signed_prekey_signature', 'signed_prekey_id')
