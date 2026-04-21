import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import requests
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from common.config import (
    FAILURE_THRESHOLD,
    MAX_RETRIES,
    RATE_LIMIT_JITTER,
    RATE_LIMIT_SECONDS,
    USER_AGENT,
)
from common.logging import get_logger
from common.spotify_auth import get_access_token
from common.supabase_client import get_admin_client


SPOTIFY_ARTIST_URL = "https://api.spotify.com/v1/artists/{id}"
ARTIST_LIST_PATH = Path(__file__).parent / "artist_list.json"
REQUEST_TIMEOUT_SECONDS = 10

logger = get_logger("fetch_metadata")


class ArtistNotFoundError(Exception):
    def __init__(self, spotify_id: str) -> None:
        self.spotify_id = spotify_id
        super().__init__(f"Spotify artist not found: {spotify_id}")


class RetryableHTTPError(Exception):
    def __init__(self, status_code: int, retry_after: float | None = None) -> None:
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(f"Retryable HTTP error {status_code}")


def _parse_retry_after(header_value: str | None) -> float | None:
    if not header_value:
        return None

    try:
        value = float(header_value)
    except ValueError:
        return None

    return value if value > 0 else None


def _extract_image_url(images: Any) -> str | None:
    if not isinstance(images, list) or not images:
        return None

    def _width(image: Any) -> int:
        if isinstance(image, dict):
            width = image.get("width")

            if isinstance(width, int):
                return width

        return 0

    best = max(images, key=_width)

    if not isinstance(best, dict):
        return None

    url = best.get("url")
    return url if isinstance(url, str) and url else None


def _extract_genres(genres: Any) -> list[str]:
    if not isinstance(genres, list):
        return []

    return [genre for genre in genres if isinstance(genre, str)]


def _fetch_one(spotify_id: str) -> dict[str, Any]:
    token = get_access_token()
    response = requests.get(
        SPOTIFY_ARTIST_URL.format(id=spotify_id),
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    if response.status_code == 404:
        raise ArtistNotFoundError(spotify_id)

    if response.status_code == 429:
        retry_after = _parse_retry_after(response.headers.get("Retry-After"))
        raise RetryableHTTPError(429, retry_after)

    if 500 <= response.status_code < 600:
        raise RetryableHTTPError(response.status_code)

    response.raise_for_status()
    return response.json()


_fallback_wait = wait_exponential(multiplier=1, min=1, max=30)


def _retry_wait(retry_state: RetryCallState) -> float:
    outcome = retry_state.outcome
    exception = outcome.exception() if outcome else None

    if isinstance(exception, RetryableHTTPError) and exception.retry_after is not None:
        return float(exception.retry_after)

    return _fallback_wait(retry_state)


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=_retry_wait,
    retry=retry_if_exception_type(
        (RetryableHTTPError, requests.Timeout, requests.ConnectionError)
    ),
    reraise=True,
)
def _fetch_with_retries(spotify_id: str) -> dict[str, Any]:
    return _fetch_one(spotify_id)


def _load_artist_list() -> list[str]:
    if not ARTIST_LIST_PATH.is_file():
        return []

    try:
        raw = ARTIST_LIST_PATH.read_text(encoding="utf-8")
    except OSError:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    return [item for item in data if isinstance(item, str) and item]


def _upsert_artist(client: Any, data: dict[str, Any]) -> None:
    payload = {
        "spotify_id": data["id"],
        "name": data["name"],
        "image_url": _extract_image_url(data.get("images")),
        "genres": _extract_genres(data.get("genres")),
    }
    client.table("artists").upsert(payload, on_conflict="spotify_id").execute()


def _mark_inactive_if_exists(client: Any, spotify_id: str) -> None:
    client.table("artists").update({"is_active": False}).eq(
        "spotify_id", spotify_id
    ).execute()


def _sleep_between_requests(index: int, total: int) -> None:
    if index >= total - 1:
        return

    delay = RATE_LIMIT_SECONDS + random.uniform(-RATE_LIMIT_JITTER, RATE_LIMIT_JITTER)

    if delay > 0:
        time.sleep(delay)


def main(artist_ids: list[str] | None = None) -> int:
    ids = _load_artist_list() if artist_ids is None else list(artist_ids)

    if not ids:
        logger.warning(
            "artist_list is empty; nothing to fetch",
            extra={"event": "artist_list_empty"},
        )
        return 0

    client = get_admin_client()

    attempted = 0
    succeeded = 0
    not_found = 0
    errors = 0

    for index, spotify_id in enumerate(ids):
        attempted += 1

        try:
            data = _fetch_with_retries(spotify_id)
        except ArtistNotFoundError:
            not_found += 1
            logger.warning(
                "artist not found on Spotify",
                extra={"event": "artist_not_found", "spotify_id": spotify_id},
            )

            try:
                _mark_inactive_if_exists(client, spotify_id)
            except Exception as mark_error:  # noqa: BLE001
                errors += 1
                logger.error(
                    "failed to mark artist inactive",
                    extra={
                        "event": "mark_inactive_error",
                        "spotify_id": spotify_id,
                        "error": str(mark_error),
                    },
                )

            _sleep_between_requests(index, len(ids))
            continue
        except RetryableHTTPError as error:
            errors += 1
            logger.error(
                "spotify request failed after retries",
                extra={
                    "event": "fetch_error",
                    "spotify_id": spotify_id,
                    "status_code": error.status_code,
                },
            )
            _sleep_between_requests(index, len(ids))
            continue
        except requests.RequestException as error:
            errors += 1
            logger.error(
                "spotify request failed after retries",
                extra={
                    "event": "fetch_error",
                    "spotify_id": spotify_id,
                    "error": str(error),
                },
            )
            _sleep_between_requests(index, len(ids))
            continue

        try:
            _upsert_artist(client, data)
        except Exception as error:  # noqa: BLE001
            errors += 1
            logger.error(
                "supabase upsert failed",
                extra={
                    "event": "upsert_error",
                    "spotify_id": spotify_id,
                    "error": str(error),
                },
            )
            _sleep_between_requests(index, len(ids))
            continue

        succeeded += 1
        _sleep_between_requests(index, len(ids))

    logger.info(
        "fetch_metadata_complete",
        extra={
            "event": "fetch_metadata_complete",
            "attempted": attempted,
            "succeeded": succeeded,
            "not_found": not_found,
            "errors": errors,
        },
    )

    if attempted == 0:
        return 0

    return 0 if (errors / attempted) <= FAILURE_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())
