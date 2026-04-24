# Pipeline Agent Notes

This is the canonical guide for AI agents editing `scripts/pipeline/`.

## Purpose

The pipeline populates and updates Spotify artist data for Label League:

- metadata comes from the Spotify Web API;
- monthly listener counts come from public Spotify artist pages because the Web API does not expose them;
- snapshots are written to Supabase for later season scoring.

## Setup

From `scripts/pipeline/`:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m playwright install-deps chromium
```

The dependency installer may need sudo on Linux/WSL. Required env vars live in the repo-root `.env.local`:

- `NEXT_PUBLIC_SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`

Never use `SUPABASE_URL`.

## Scripts

- `fetch_metadata.py` reads `artist_list.json`, calls Spotify Web API, and upserts artist name/image/genres into `artists`.
- `scrape_listeners.py` queries Supabase for `artists` where `is_active = true` and `opted_out = false`, scrapes listener counts, and inserts into `listener_snapshots`.
- `run_daily.py` runs metadata fetch then listener scrape, logs `daily_pipeline_complete`, and exits 0 only if both sub-scripts succeeded.
- `smoke_spotify_auth.py` prints a Spotify token to verify credentials. Do not paste tokens into commits or logs.

The scraper does not read `artist_list.json`; it reads active artists from Supabase.

## Shared Infrastructure

- `common/config.py` loads repo-root `.env.local` by walking upward from the current directory.
- `common/logging.py` emits one-line JSON logs. Use `get_logger(name)` and put stable context in `extra`, including an `event` key.
- `common/spotify_auth.py` caches Spotify client-credentials tokens and refreshes near expiry.
- `common/supabase_client.py` returns a memoized service-role Supabase client.

## Logging

Use structured logs:

```python
logger.info(
    "snapshot captured",
    extra={"event": "snapshot_captured", "artist_id": artist_id, "listeners": listeners},
)
```

Downstream consumers should filter on `event`, not the human message. Do not log secrets, tokens, cookies, or auth headers.

## Retry And Exit Codes

Network scripts use Tenacity with `MAX_RETRIES = 3` from `common/config.py`.

- Honor numeric `Retry-After` on 429 responses.
- Retry connection errors, timeouts, and retryable HTTP errors.
- Do not retry arbitrary exceptions without a concrete reason.

Scripts compute an error rate and return `0` when it is at or below `FAILURE_THRESHOLD = 0.10`, otherwise `1`. Preserve this convention for new pipeline entrypoints.

`run_daily.py` intentionally runs `scrape_listeners` even if `fetch_metadata` fails, because the scraper reads existing active artists from Supabase.

## Scraper Fragility

`scrape_listeners.py` is intentionally marked fragile. The static `requests` fetch often returns a Spotify web-player shell, so the scraper falls back to Playwright-rendered Chromium when parsing static HTML fails.

Parser strategy order in `parsers/strategies.py`:

1. `meta_description`
2. `next_data`
3. `json_ld`
4. `inline_json`
5. `body_text`

Update parser tests and fixtures when Spotify HTML changes. Long term, replace scraping with a licensed data provider such as Songstats, Chartmetric, or Soundcharts.

## Tests

From `scripts/pipeline/`:

```bash
python -m py_compile fetch_metadata.py scrape_listeners.py run_daily.py common/*.py parsers/*.py
python -m pytest tests/
```

Parser fixtures live in `tests/fixtures/`. `conftest.py` sets `sys.path` so local imports work.

## Safety

- Do not run write-capable scripts against production unless the user explicitly confirms it.
- `scrape_listeners.py --limit N` writes real `listener_snapshots` rows.
- `fetch_metadata.py` upserts `artists` and may mark missing artists inactive.
- Keep service-role usage confined to trusted scripts.
