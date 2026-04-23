# Label League — agent notes

See `README.md` for the product pitch, stack, and setup steps. This file captures what an agent needs to navigate the repo and avoid pitfalls.

## Repo layout

- `app/` — Next.js 15 App Router (pages, layouts, server actions)
- `components/` — React components; shadcn/ui primitives live under `components/ui/`
- `lib/` — TypeScript utilities, including the Supabase client setup
- `supabase/` — SQL migrations (`0001_initial_schema.sql`, `0002_tier_function.sql`). Migrations are the source of truth for the schema.
- `scripts/pipeline/` — Python data pipeline (Spotify metadata + listener scraping). Has its own `CLAUDE.md`.
- `public/` — static assets

## Tooling

- Package manager is **pnpm** — not npm or yarn. Use `pnpm install`, `pnpm dev`.
- Prettier (`.prettierrc`) and ESLint flat config (`eslint.config.mjs`). TypeScript is strict.
- Pipeline uses Python 3 with the version pinned in `.python-version`. Deps in `scripts/pipeline/requirements.txt` (install via `pip install -r`, and `playwright install chromium` on first setup).

## Environment

`.env.local` at the repo root is shared by frontend and pipeline. Template: `.env.local.example`. Required:

- `NEXT_PUBLIC_SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (pipeline only — never expose to frontend)
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`

Optional: `LOG_LEVEL` (pipeline, default `INFO`).

## Database

Supabase. Two tables matter for the pipeline:

- `artists` — `spotify_id`, `name`, `image_url`, `genres`, `is_active`, `opted_out`
- `listener_snapshots` — `artist_id`, `monthly_listeners`, `captured_at`

## Running things

- Frontend: `pnpm dev`
- Pipeline: see `scripts/pipeline/README.md`

## Conventions

- Match the existing style in the file you're editing; don't introduce abstractions a task doesn't need.
- Never commit `.env.local`, `node_modules/`, or Python `__pycache__/`.
- Secrets stay in `.env.local` — never hardcoded, never logged.
