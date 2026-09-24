from playhouse.db_url import connect

from app.core.config import DATABASE_URL

db = connect(DATABASE_URL, max_connections=20, stale_timeout=300)  # type: ignore[no-untyped-call]
