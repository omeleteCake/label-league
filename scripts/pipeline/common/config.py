import os
from pathlib import Path

from dotenv import load_dotenv


def _find_env_file(filename: str = ".env.local") -> Path | None:
    for directory in (Path.cwd(), *Path.cwd().parents):
        candidate = directory / filename

        if candidate.is_file():
            return candidate

    return None


def _required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


_env_file = _find_env_file()

if _env_file:
    load_dotenv(_env_file)

NEXT_PUBLIC_SUPABASE_URL = _required_env("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = _required_env("SUPABASE_SERVICE_ROLE_KEY")
SPOTIFY_CLIENT_ID = _required_env("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = _required_env("SPOTIFY_CLIENT_SECRET")

RATE_LIMIT_SECONDS = 2.0
RATE_LIMIT_JITTER = 0.5
MAX_RETRIES = 3
FAILURE_THRESHOLD = 0.10
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
