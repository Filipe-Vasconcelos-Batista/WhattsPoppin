import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parents[2]

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+pool://whattspoppin:whattspoppin@localhost:5432/whattspoppin"
)

SERVER_NAME = os.environ.get("SERVER_NAME", "localhost:8000").strip().lower()

SERVER_SIGNING_KEY_PATH = Path(
    os.environ.get("SERVER_SIGNING_KEY_PATH", str(BACKEND_DIR / "data" / "signing.key"))
)

SERVER_MODE_PRIVATE = "private"
SERVER_MODE_DIRECTORY = "directory"
SERVER_MODE = os.environ.get("SERVER_MODE", SERVER_MODE_PRIVATE).strip().lower()
if SERVER_MODE not in (SERVER_MODE_PRIVATE, SERVER_MODE_DIRECTORY):
    raise RuntimeError(f"SERVER_MODE inválido: {SERVER_MODE!r} (private ou directory)")

FEDERATION_ALLOW_HTTP = os.environ.get("FEDERATION_ALLOW_HTTP", "false").strip().lower() == "true"
