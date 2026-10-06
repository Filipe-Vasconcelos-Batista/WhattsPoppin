import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parents[2]

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+pool://whattspoppin:whattspoppin@localhost:5432/whattspoppin"
)

SERVER_NAME = os.environ.get("SERVER_NAME", "localhost:8000").strip().lower()

# Fora da BD de propósito: um dump roubado não chega para alguém se fazer
# passar pelo servidor. Um caminho relativo conta a partir de onde o uvicorn corre.
SERVER_SIGNING_KEY_PATH = Path(
    os.environ.get("SERVER_SIGNING_KEY_PATH", str(BACKEND_DIR / "data" / "signing.key"))
)

# Só os .env de dev o ligam; em produção a federação exige HTTPS.
FEDERATION_ALLOW_HTTP = os.environ.get("FEDERATION_ALLOW_HTTP", "false").strip().lower() == "true"
