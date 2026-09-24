import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+pool://whattspoppin:whattspoppin@localhost:5432/whattspoppin"
)
