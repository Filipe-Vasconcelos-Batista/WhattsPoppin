import peewee as pw

from app.db import db


class BaseModel(pw.Model):
    class Meta:
        database = db
