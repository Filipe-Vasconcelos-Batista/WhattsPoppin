"""Força os testes a correr numa BD própria (TEST_DATABASE_URL), nunca na de
dev. Tem de correr antes de qualquer módulo importar `app`, porque
`app.db` liga-se a DATABASE_URL no momento do import."""

import os
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR.parent / ".env")

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    pytest.exit(
        "TEST_DATABASE_URL não está definido - acrescenta-o ao .env (ver .env.example)",
        returncode=1,
    )

_test_db_name = urlparse(TEST_DATABASE_URL).path.lstrip("/")
if not _test_db_name.endswith("_test"):
    pytest.exit(
        f'TEST_DATABASE_URL aponta para "{_test_db_name}" - o nome tem de acabar em "_test" '
        "para os testes nunca tocarem na BD de dev por engano",
        returncode=1,
    )

os.environ["DATABASE_URL"] = TEST_DATABASE_URL

MIGRATE_TABLE = "migratehistory"


@pytest.fixture(scope="session", autouse=True)
def _prepare_test_database() -> Iterator[None]:
    from peewee_migrate import Router

    from app.db import db

    Router(db, migrate_dir=BACKEND_DIR / "migrations", ignore=["basemodel"]).run()

    tables = [table for table in db.get_tables() if table != MIGRATE_TABLE]
    if tables:
        quoted = ", ".join(f'"{table}"' for table in tables)
        db.execute_sql(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE")
    yield


# Fora de um `with`, o TestClient abre cada WebSocket no seu próprio event
# loop, e uma mensagem enviada do handler de um socket para outro nunca
# acorda quem está à espera (bloqueia para sempre). Dentro do `with` todos
# partilham um só loop, como no uvicorn.
@pytest.fixture
def ws_client() -> Iterator[TestClient]:
    from app.main import app

    with TestClient(app) as shared:
        yield shared
