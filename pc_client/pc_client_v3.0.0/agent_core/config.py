import os
from pathlib import Path

from dotenv import load_dotenv


def load_env():
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parents[3] / ".env",
    ]
    for path in candidates:
        if path.exists():
            load_dotenv(path, override=False)


def get_database_url():
    load_env()
    return normalize_database_url(os.getenv("DATABASE_URL", ""))


def normalize_database_url(url):
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url
