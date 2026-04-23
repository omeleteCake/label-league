# Pipeline — agent notes

See `README.md` in this directory for install and run commands. This file captures non-obvious patterns that are easy to break.

## Scripts

- `fetch_metadata.py` — reads `artist_list.json`, upserts artist name/image/genres from Spotify Web API into `artists`.
- `scrape_listeners.py` — scrapes monthly listener counts from `open.spotify.com/artist/{id}` for active, non-opted-out artists; writes to `listener_snapshots`.
- `run_daily.py` — orchestrator. Runs `fetch_metadata` then `scrape_listeners`, logs a `daily_pipeline_complete` summary.
- `smoke_spotify_auth.py` — prints a Spotify token to verify credentials.

## Shared infra (`common/`)

- `common/config.py` — loads `.env.local` (searched up the tree) and exposes constants: `RATE_LIMIT_SECONDS`, `RATE_LIMIT_JITTER`, `MAX_RETRIES=3`, `FAILURE_THRESHOLD=0.10`, `USER_AGENT`.
- `common/logging.py` — JSON formatter. Use `get_logger(name)` everywhere; don't call `logging.basicConfig` yourself.
- `common/spotify_auth.py` — cached client-credentials token; refreshes when <60s remain. Module-level globals are intentional.
- `common/supabase_client.py` — `get_admin_client()` returns a lazy singleton admin client (service role key).

## Logging pattern

Always pass structured context via `extra` with a stable `event` key:

```python
logger.info("fetch_metadata_complete", extra={"event": "fetch_metadata_complete", "attempted": n, "errors": e})
```

`extra` keys become top-level JSON fields. Non-scalar values are stringified by `_json_safe()`. Use `event` as the stable filter key downstream — don't rely on the free-text message.

## Retry pattern

Tenacity with a custom `_retry_wait()` that:

1. Honors `Retry-After` (seconds) from 429 responses when present.
2. Falls back to exponential backoff.

Retry only on `RetryableHTTPError`, `requests.Timeout`, `requests.ConnectionError` — not on arbitrary exceptions. `MAX_RETRIES=3` via `common/config.py`; don't bump it without a reason.

## Exit-code convention

Each script computes an error rate (`errors / attempted` or equivalent) and returns `0` if it's ≤ `FAILURE_THRESHOLD`, else `1`. `run_daily.py` aggregates: exits `0` only if both sub-scripts did. **Preserve this when adding new pipeline scripts** — the orchestrator and any future cron/monitor depend on it.

## Orchestration invariant

`run_daily.py` runs `scrape_listeners` **even when `fetch_metadata` fails**. The scraper reads active artists from the DB directly, so it does not depend on a successful metadata refresh. Don't "fix" this by short-circuiting on the first failure.

## The scraper is fragile — intentionally

`scrape_listeners.py`'s module docstring flags this. It tries five parse strategies from `parsers/strategies.py` in order:

1. `parse_meta_description` — `<meta property="og:description">`
2. `parse_next_data` — `<script id="__NEXT_DATA__">` (Spotify is Next.js)
3. `parse_json_ld` — `<script type="application/ld+json">`
4. `parse_inline_json` — regex on `"monthlyListeners": N`
5. `parse_body_text` — regex on visible text (`"N monthly listeners"`)

If static HTML fails, it falls back to Playwright (rendered page). Update `parsers/strategies.py` when Spotify's HTML changes. Long-term replacement: Songstats / Chartmetric / Soundcharts.

## Data flow

- `artist_list.json` — JSON array of Spotify IDs; the seed for `fetch_metadata.py`. Missing or empty → warning + exit 0 (not an error).
- The scraper does **not** read this file. It queries `artists` where `is_active = true AND opted_out = false`.

## Tests

From `scripts/pipeline/`: `python -m pytest tests/`. Parser fixtures in `tests/fixtures/` are real Spotify HTML snapshots; tests skip cleanly when the fixtures directory is absent. `conftest.py` at the pipeline root sets `sys.path` so `from parsers.strategies import ...` works.

## Secrets

Never log tokens or the service role key. The cached-token pattern in `spotify_auth.py` uses module-level globals on purpose — don't refactor it into a class without a concrete reason.
