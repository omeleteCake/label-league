# Project Context

Label League is a prediction game about Spotify monthly listener growth. Players try to identify artists before they grow, then compete on roster performance over a fixed season.

## Game Shape

- A season lasts 90 days.
- The first 14 days are the signing window.
- During the signing window, players build rosters from the current artist pool.
- Once the signing window closes, rosters are locked.
- Scores are based on listener growth from signing/start baselines to later snapshots.

The core fantasy is not picking the biggest artist. It is finding artists with meaningful relative growth before everyone else notices.

## Artists And Listener Data

`artists` is the global catalog of tracked Spotify artists. Artists can be inactive or opted out.

`listener_snapshots` is append-only. Each row captures an artist's monthly listener count at a point in time. Latest listener counts should be derived with ordering/window queries rather than updating a current-count column.

Spotify's Web API does not expose monthly listener counts, so the current pipeline parses public `open.spotify.com/artist/{id}` pages. This is intentionally treated as fragile. Long-term production-grade data should come from a licensed provider such as Songstats, Chartmetric, or Soundcharts.

## Tiers

Artist tiers are based on monthly listener lower bounds:

- `underground`: 10,000+
- `rising`: 100,000+
- `emerging`: 1,000,000+
- `established`: 10,000,000+

Below 10,000 listeners, `compute_tier()` returns `NULL`.

TypeScript tier logic in `lib/tiers.ts` should mirror the SQL function in `supabase/migrations/0002_tier_function.sql`.

## Rosters And Signings

Players have one roster per season. A signing records:

- the roster;
- the artist;
- slots committed;
- the tier at signing time;
- listeners at signing time;
- when the artist was signed and optionally dropped.

`tier_at_signing` is stored as historical data. Do not convert it to a generated/current tier.

## Scoring

The project description defines scoring as weighted log-growth of the roster over the season. Keep scoring implementations explicit and testable, because this is the game's core contract.

Use `season_scores` for computed standings. It is a regular mutable table with `updated_at` so scores can be recomputed cleanly.

## Badges

Badges are immutable awards for notable outcomes:

- `first_believer`
- `tier_jump`

Badges should be inserted once and not updated in place.

## Opt-Outs And Safety

Artists can request opt-out review through `opt_out_requests`. Requests are public-write, admin-read via service role. The final result should update artist visibility through trusted server-side code only.

Never expose service-role behavior to the browser.
