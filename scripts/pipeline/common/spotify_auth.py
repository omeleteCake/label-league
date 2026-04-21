import time
from typing import Any

import requests

from common.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET


SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
TOKEN_REFRESH_BUFFER_SECONDS = 60

_access_token: str | None = None
_expires_at = 0.0


class SpotifyAuthError(RuntimeError):
    def __init__(self, status_code: int, response_body: str) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"Spotify auth failed with status {status_code}: {response_body}")


def _extract_token(
    response_body: dict[str, Any],
    status_code: int,
    raw_body: str,
) -> tuple[str, int]:
    access_token = response_body.get("access_token")
    expires_in = response_body.get("expires_in")

    if not isinstance(access_token, str) or not access_token:
        raise SpotifyAuthError(status_code, raw_body)

    if not isinstance(expires_in, int) or expires_in <= 0:
        raise SpotifyAuthError(status_code, raw_body)

    return access_token, expires_in


def get_access_token() -> str:
    global _access_token, _expires_at

    now = time.time()

    if _access_token and now < _expires_at - TOKEN_REFRESH_BUFFER_SECONDS:
        return _access_token

    try:
        response = requests.post(
            SPOTIFY_TOKEN_URL,
            auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            timeout=10,
        )
    except requests.RequestException as error:
        raise SpotifyAuthError(0, str(error)) from error

    if not response.ok:
        raise SpotifyAuthError(response.status_code, response.text)

    try:
        response_body = response.json()
    except ValueError as error:
        raise SpotifyAuthError(response.status_code, response.text) from error

    access_token, expires_in = _extract_token(response_body, response.status_code, response.text)

    _access_token = access_token
    _expires_at = now + expires_in

    return access_token
