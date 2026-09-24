"""Peewee migrations -- 001_initial.py.

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
    
    @migrator.create_model
    class Conversation(pw.Model):
        id = pw.UUIDField(primary_key=True)
        is_group = pw.BooleanField(default=False)
        created_at = pw.DateTimeField()

        class Meta:
            table_name = "conversations"

    @migrator.create_model
    class User(pw.Model):
        id = pw.UUIDField(primary_key=True)
        display_name = pw.CharField(max_length=80)
        identity_public_key = pw.BlobField()
        created_at = pw.DateTimeField()

        class Meta:
            table_name = "users"

    @migrator.create_model
    class ConversationParticipant(pw.Model):
        conversation = pw.ForeignKeyField(column_name='conversation_id', field='id', model=migrator.orm['conversations'], on_delete='CASCADE')
        user = pw.ForeignKeyField(column_name='user_id', field='id', model=migrator.orm['users'], on_delete='CASCADE')
        joined_at = pw.DateTimeField()

        class Meta:
            table_name = "conversation_participants"
            primary_key = pw.CompositeKey('conversation', 'user')

    @migrator.create_model
    class Device(pw.Model):
        id = pw.UUIDField(primary_key=True)
        user = pw.ForeignKeyField(column_name='user_id', field='id', model=migrator.orm['users'], on_delete='CASCADE')
        name = pw.CharField(max_length=80, null=True)
        is_active = pw.BooleanField(default=True)
        registered_at = pw.DateTimeField()
        last_seen_at = pw.DateTimeField(null=True)

        class Meta:
            table_name = "devices"


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""
    
    migrator.remove_model('devices')

    migrator.remove_model('conversation_participants')

    migrator.remove_model('users')

    migrator.remove_model('conversations')
