import uuid

import peewee as pw

from app.models.base import BaseModel
from app.models.device import Device


class OneTimePrekey(BaseModel):
    id = pw.UUIDField(primary_key=True, default=uuid.uuid4)
    device = pw.ForeignKeyField(Device, backref="one_time_prekeys", on_delete="CASCADE")
    key_id = pw.IntegerField()
    public_key = pw.BlobField()

    class Meta:
        table_name = "one_time_prekeys"
