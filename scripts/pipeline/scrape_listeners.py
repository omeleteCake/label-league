"""
Fragile public-HTML scraper. Expects Spotify's artist page HTML format as of 2026.
If parse_failures consistently exceed the threshold, update parsers/strategies.py.
Long-term: replace with a licensed data provider (Songstats, Chartmetric, Soundcharts).
"""

import argparse
import random
import sys
import time
from datetime import UTC, datetime
from typing import Any

import requests
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
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
from common.supabase_client import get_admin_client
from parsers.strategies import try_parse


SPOTIFY_ARTIST_PAGE_URL = "https://open.spotify.com/artist/{id}"
REQUEST_TIMEOUT_SECONDS = 15
BROWSER_PAGE_TIMEOUT_MS = 45_000
BROWSER_NETWORK_IDLE_TIMEOUT_MS = 15_000
BROWSER_POST_LOAD_SETTLE_MS = 5_000

logger = get_logger("scrape_listeners")


class ArtistNotFoundError(Exception):
    def __init__(self, spotify_id: str) -> None:
        self.spotify_id = spotify_id
        super().__init__(f"Spotify artist page not found: {spotify_id}")


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


def _fetch_one(spotify_id: str) -> str:
    response = requests.get(
        SPOTIFY_ARTIST_PAGE_URL.format(id=spotify_id),
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
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
    return response.text


_fallback_wait = wait_exponential(multiplier=2, min=2, max=60)


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
def _fetch_with_retries(spotify_id: str) -> str:
    return _fetch_one(spotify_id)


class SpotifyBrowserFetcher:
    def __init__(self) -> None:
        self._playwright: Any | None = None
        self._browser: Any | None = None
        self._context: Any | None = None
        self._page: Any | None = None

    def fetch(self, spotify_id: str) -> str:
        page = self._ensure_page()
        response = page.goto(
            SPOTIFY_ARTIST_PAGE_URL.format(id=spotify_id),
            wait_until="domcontentloaded",
            timeout=BROWSER_PAGE_TIMEOUT_MS,
        )

        status_code = response.status if response else None

        if status_code == 404:
            raise ArtistNotFoundError(spotify_id)

        if status_code == 429:
            retry_after = (
                _parse_retry_after(response.headers.get("Retry-After")) if response else None
            )
            raise RetryableHTTPError(429, retry_after)

        if status_code is not None and 500 <= status_code < 600:
            raise RetryableHTTPError(status_code)

        if status_code is not None and status_code >= 400:
            raise requests.HTTPError(f"Rendered Spotify artist page returned HTTP {status_code}")

        try:
            page.wait_for_load_state("networkidle", timeout=BROWSER_NETWORK_IDLE_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            pass

        page.wait_for_timeout(BROWSER_POST_LOAD_SETTLE_MS)
        return page.content()

    def close(self) -> None:
        for handle_name in ("_context", "_browser"):
            handle = getattr(self, handle_name)

            if handle is None:
                continue

            try:
                handle.close()
            except PlaywrightError:
                pass

            setattr(self, handle_name, None)

        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

        self._page = None

    def _ensure_page(self) -> Any:
        if self._page is not None:
            return self._page

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._context = self._browser.new_context(
            user_agent=USER_AGENT,
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        self._page = self._context.new_page()

        return self._page


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=_retry_wait,
    retry=retry_if_exception_type((RetryableHTTPError, PlaywrightTimeoutError)),
    reraise=True,
)
def _fetch_rendered_with_retries(
    browser_fetcher: SpotifyBrowserFetcher,
    spotify_id: str,
) -> str:
    return browser_fetcher.fetch(spotify_id)


def _sleep_between_requests(index: int, total: int) -> None:
    if index >= total - 1:
        return

    delay = RATE_LIMIT_SECONDS + random.uniform(-RATE_LIMIT_JITTER, RATE_LIMIT_JITTER)
    time.sleep(max(0.0, delay))


def _filter_artist_rows(
    data: Any,
    spotify_ids: list[str] | None,
) -> list[dict[str, str]]:
    if not isinstance(data, list):
        raise RuntimeError("Supabase artists query returned non-list data")

    order = {spotify_id: index for index, spotify_id in enumerate(spotify_ids or [])}

    artists: list[dict[str, str]] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        artist_id = item.get("id")
        spotify_id = item.get("spotify_id")

        if isinstance(artist_id, str) and isinstance(spotify_id, str):
            artists.append({"id": artist_id, "spotify_id": spotify_id})

    if spotify_ids is not None:
        artists.sort(key=lambda artist: order.get(artist["spotify_id"], len(order)))

    return artists


def _load_active_artists(
    client: Any,
    limit: int | None,
    spotify_ids: list[str] | None = None,
) -> list[dict[str, str]]:
    query = (
        client.table("artists")
        .select("id, spotify_id")
        .eq("is_active", True)
        .eq("opted_out", False)
    )

    if spotify_ids:
        query = query.in_("spotify_id", spotify_ids)

    response = query.execute()
    artists = _filter_artist_rows(response.data, spotify_ids)

    return artists[:limit] if limit is not None else artists


def _mark_artist_inactive(client: Any, artist_id: str) -> None:
    client.table("artists").update({"is_active": False}).eq("id", artist_id).execute()


def _insert_snapshot(client: Any, artist_id: str, listeners: int) -> None:
    client.table("listener_snapshots").insert(
        {
            "artist_id": artist_id,
            "monthly_listeners": listeners,
            "captured_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
    ).execute()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Spotify monthly listener counts.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N active artists.",
    )
    return parser.parse_args()


def main(limit: int | None = None, spotify_ids: list[str] | None = None) -> int:
    client = get_admin_client()

    try:
        artists = _load_active_artists(client, limit, spotify_ids)
    except Exception as error:  # noqa: BLE001
        logger.error(
            "failed to load active artists",
            extra={"event": "database_error", "operation": "load_artists", "error": str(error)},
        )
        return 1

    attempted = len(artists)
    succeeded = 0
    parse_failures = 0
    http_errors = 0
    not_found = 0
    strategy_counts: dict[str, int] = {}
    browser_fetcher: SpotifyBrowserFetcher | None = None

    for index, artist in enumerate(artists):
        artist_id = artist["id"]
        spotify_id = artist["spotify_id"]

        try:
            html = _fetch_with_retries(spotify_id)
        except ArtistNotFoundError:
            not_found += 1
            logger.warning(
                "artist page not found",
                extra={
                    "event": "artist_not_found",
                    "artist_id": artist_id,
                    "spotify_id": spotify_id,
                },
            )

            try:
                _mark_artist_inactive(client, artist_id)
            except Exception as error:  # noqa: BLE001
                http_errors += 1
                logger.error(
                    "failed to mark artist inactive",
                    extra={
                        "event": "database_error",
                        "operation": "mark_inactive",
                        "artist_id": artist_id,
                        "spotify_id": spotify_id,
                        "error": str(error),
                    },
                )

            _sleep_between_requests(index, attempted)
            continue
        except RetryableHTTPError as error:
            http_errors += 1
            logger.error(
                "spotify artist page request failed after retries",
                extra={
                    "event": "http_error",
                    "artist_id": artist_id,
                    "spotify_id": spotify_id,
                    "status_code": error.status_code,
                },
            )
            _sleep_between_requests(index, attempted)
            continue
        except requests.HTTPError as error:
            http_errors += 1
            status_code = error.response.status_code if error.response is not None else None
            logger.error(
                "spotify artist page request failed",
                extra={
                    "event": "http_error",
                    "artist_id": artist_id,
                    "spotify_id": spotify_id,
                    "status_code": status_code,
                    "error": str(error),
                },
            )
            _sleep_between_requests(index, attempted)
            continue
        except requests.RequestException as error:
            http_errors += 1
            logger.error(
                "spotify artist page request failed after retries",
                extra={
                    "event": "http_error",
                    "artist_id": artist_id,
                    "spotify_id": spotify_id,
                    "error": str(error),
                },
            )
            _sleep_between_requests(index, attempted)
            continue

        source = "requests"
        parsed = try_parse(html)

        if parsed is None:
            logger.info(
                "static Spotify HTML did not include monthly listener count; trying rendered page",
                extra={
                    "event": "rendered_fetch_attempt",
                    "artist_id": artist_id,
                    "spotify_id": spotify_id,
                },
            )

            if browser_fetcher is None:
                browser_fetcher = SpotifyBrowserFetcher()

            try:
                html = _fetch_rendered_with_retries(browser_fetcher, spotify_id)
            except ArtistNotFoundError:
                not_found += 1
                logger.warning(
                    "artist page not found",
                    extra={
                        "event": "artist_not_found",
                        "artist_id": artist_id,
                        "spotify_id": spotify_id,
                        "source": "playwright",
                    },
                )

                try:
                    _mark_artist_inactive(client, artist_id)
                except Exception as error:  # noqa: BLE001
                    http_errors += 1
                    logger.error(
                        "failed to mark artist inactive",
                        extra={
                            "event": "database_error",
                            "operation": "mark_inactive",
                            "artist_id": artist_id,
                            "spotify_id": spotify_id,
                            "error": str(error),
                        },
                    )

                _sleep_between_requests(index, attempted)
                continue
            except RetryableHTTPError as error:
                http_errors += 1
                logger.error(
                    "rendered Spotify artist page request failed after retries",
                    extra={
                        "event": "http_error",
                        "artist_id": artist_id,
                        "spotify_id": spotify_id,
                        "source": "playwright",
                        "status_code": error.status_code,
                    },
                )
                _sleep_between_requests(index, attempted)
                continue
            except requests.HTTPError as error:
                http_errors += 1
                logger.error(
                    "rendered Spotify artist page request failed",
                    extra={
                        "event": "http_error",
                        "artist_id": artist_id,
                        "spotify_id": spotify_id,
                        "source": "playwright",
                        "error": str(error),
                    },
                )
                _sleep_between_requests(index, attempted)
                continue
            except PlaywrightError as error:
                http_errors += 1
                logger.error(
                    "rendered Spotify artist page request failed",
                    extra={
                        "event": "http_error",
                        "artist_id": artist_id,
                        "spotify_id": spotify_id,
                        "source": "playwright",
                        "error": str(error),
                    },
                )
                browser_fetcher.close()
                browser_fetcher = None
                _sleep_between_requests(index, attempted)
                continue

            source = "playwright"
            parsed = try_parse(html)

        if parsed is None:
            parse_failures += 1
            logger.error(
                "monthly listener parse failed",
                extra={
                    "event": "parse_failed",
                    "artist_id": artist_id,
                    "spotify_id": spotify_id,
                    "source": source,
                },
            )
            _sleep_between_requests(index, attempted)
            continue

        listeners, strategy = parsed

        try:
            _insert_snapshot(client, artist_id, listeners)
        except Exception as error:  # noqa: BLE001
            http_errors += 1
            logger.error(
                "failed to insert listener snapshot",
                extra={
                    "event": "database_error",
                    "operation": "insert_snapshot",
                    "artist_id": artist_id,
                    "spotify_id": spotify_id,
                    "listeners": listeners,
                    "strategy": strategy,
                    "source": source,
                    "error": str(error),
                },
            )
            _sleep_between_requests(index, attempted)
            continue

        succeeded += 1
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        logger.info(
            "snapshot captured",
            extra={
                "event": "snapshot_captured",
                "artist_id": artist_id,
                "spotify_id": spotify_id,
                "listeners": listeners,
                "strategy": strategy,
                "source": source,
            },
        )
        _sleep_between_requests(index, attempted)

    if browser_fetcher is not None:
        browser_fetcher.close()

    logger.info(
        "scrape complete",
        extra={
            "event": "scrape_complete",
            "attempted": attempted,
            "succeeded": succeeded,
            "parse_failures": parse_failures,
            "http_errors": http_errors,
            "not_found": not_found,
            "strategy_counts": strategy_counts,
        },
    )

    if attempted == 0:
        return 0

    failure_rate = (parse_failures + http_errors) / attempted
    return 0 if failure_rate <= FAILURE_THRESHOLD else 1


if __name__ == "__main__":
    args = _parse_args()
    sys.exit(main(limit=args.limit))
