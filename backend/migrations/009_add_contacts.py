"""Peewee migrations -- 009_add_contacts.py."""


from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):

    @migrator.create_model
    class Contact(pw.Model):
        owner = pw.ForeignKeyField(column_name='owner_id', field='id', model=migrator.orm['users'], on_delete='CASCADE', backref='+')
        contact = pw.ForeignKeyField(column_name='contact_id', field='id', model=migrator.orm['users'], on_delete='CASCADE', backref='+', index=True)
        status = pw.CharField(max_length=16)
        created_at = pw.DateTimeField()
        updated_at = pw.DateTimeField()

        class Meta:
            table_name = "contacts"
            primary_key = pw.CompositeKey('owner', 'contact')


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):

    migrator.remove_model('contacts')
