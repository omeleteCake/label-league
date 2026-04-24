# Runbook

Operational notes for local development, AI agents, and future maintainers.

## Local App Setup

```bash
nvm use
pnpm install
cp .env.local.example .env.local
pnpm dev
```

Fill `.env.local` with the production env var names from `.env.local.example`.

## Frontend Checks

```bash
pnpm lint
pnpm exec tsc --noEmit
pnpm test
pnpm build
```

Use `pnpm exec prettier --check .` for formatting checks, or `pnpm format` when intentionally rewriting formatting.

## Database

Migrations live in `supabase/migrations/`.

Apply migrations only against the intended Supabase project. Do not create migrations as a side effect of frontend or pipeline work.

`lib/types/database.ts` is hand-written and must be updated manually when migrations change.

## Pipeline Setup

From `scripts/pipeline/`:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m playwright install-deps chromium
```

`install-deps` may require sudo on Linux/WSL.

## Pipeline Checks

```bash
cd scripts/pipeline
python -m py_compile fetch_metadata.py scrape_listeners.py run_daily.py common/*.py parsers/*.py
python -m pytest tests/
```

## Pipeline Commands

```bash
cd scripts/pipeline
python smoke_spotify_auth.py
python fetch_metadata.py
python scrape_listeners.py --limit 5
python run_daily.py
```

Write-capable commands:

- `fetch_metadata.py` upserts `artists` and may mark missing artists inactive.
- `scrape_listeners.py` inserts `listener_snapshots`.
- `run_daily.py` runs both.

Only run these against production when that is explicitly intended.

## Dev Seed Script

The TypeScript seed script is destructive for development data:

```bash
pnpm tsx scripts/seed_dev.ts
```

It clears and recreates dev rows in pipeline/game tables. Do not run it against production.

## Vercel And Supabase

Vercel builds the Next.js app only. Python pipeline scripts are local/server-job tooling, not part of the Vercel build.

If `/api/health` works locally but fails on Vercel, check Vercel environment variables first:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

The service role key is for trusted server-side jobs only and must not be exposed to client code.

## Agent Safety Checklist

Before committing:

```bash
git status --short
git diff --check
```

Stage only intended files. Preserve user changes. Do not commit generated caches such as `.next/`, `.pytest_cache/`, `__pycache__/`, virtualenvs, or `node_modules/`.
