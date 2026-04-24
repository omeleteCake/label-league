# Agent Notes

This is the canonical repo guide for AI coding agents. Keep it short, accurate, and in sync with the code.

## Project

Label League is a 90-day prediction league over Spotify monthly listener growth. Players sign artists during a 14-day window, then rosters are scored on weighted log-growth over the season.

Read more:

- `README.md` — human setup summary.
- `docs/PROJECT_CONTEXT.md` — product and domain context.
- `docs/RUNBOOK.md` — local commands, checks, and operational notes.
- `scripts/pipeline/AGENTS.md` — Python pipeline-specific instructions.

## Repo Layout

- `app/` — Next.js 15 App Router routes and pages.
- `components/` — React components; shadcn/ui primitives live in `components/ui/`.
- `lib/` — TypeScript utilities, typed domain helpers, and Supabase client setup.
- `supabase/migrations/` — SQL migrations. These are the source of truth for database shape.
- `scripts/pipeline/` — Python data pipeline for Spotify metadata and listener snapshots.
- `scripts/seed_dev.ts` — destructive local/dev seed script.
- `public/` — static assets.

## Tooling

- Use `pnpm`, not npm or yarn.
- Node is pinned to 20 via `.nvmrc`.
- TypeScript is strict and has `noUncheckedIndexedAccess` enabled.
- Import alias is `@/*`, with no `src/` directory.
- Formatting is Prettier; linting is ESLint.
- Pipeline Python version is pinned in `.python-version`; dependencies are in `scripts/pipeline/requirements.txt`.

Common checks:

```bash
pnpm lint
pnpm exec tsc --noEmit
pnpm test
pnpm build
cd scripts/pipeline && python -m pytest tests/
```

## Environment

`.env.local` lives at the repo root and is shared by the app and pipeline. Template: `.env.local.example`.

Use these names exactly:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`

Use `NEXT_PUBLIC_SUPABASE_URL` everywhere a Supabase project URL is needed, including trusted scripts.

## Safety Rules

- Never commit `.env.local`, secrets, `node_modules/`, `.next/`, Python virtualenvs, or `__pycache__/`.
- Never expose or log `SUPABASE_SERVICE_ROLE_KEY`, Spotify secrets, bearer tokens, cookies, or auth headers.
- Do not create browser or admin Supabase clients unless a task explicitly asks for them.
- Do not add migrations, middleware, or destructive scripts unless explicitly requested.
- Do not run `scripts/seed_dev.ts` or pipeline commands that write to Supabase against production unless the user explicitly confirms the target is safe.
- Preserve existing user changes. If the worktree is dirty, understand the diff before editing and stage only intended files.

## Database Notes

The schema source of truth is:

- `supabase/migrations/0001_initial_schema.sql`
- `supabase/migrations/0002_tier_function.sql`
- `lib/types/database.ts` mirrors those migrations manually and must be kept in sync.

Important pipeline tables:

- `artists` — global tracked Spotify catalog with `spotify_id`, `name`, `genres`, `is_active`, and `opted_out`.
- `listener_snapshots` — append-only monthly listener measurements.
- `seasons`, `rosters`, `signings`, `season_scores`, `badges` — league state and scoring outputs.

## Development Defaults

- Match local code style and avoid broad refactors.
- Prefer small, focused tests close to changed logic.
- Use structured APIs/parsers where available.
- For frontend work, keep the existing shadcn/Tailwind conventions and avoid custom CSS unless needed.
- For pipeline work, follow `scripts/pipeline/AGENTS.md`.
