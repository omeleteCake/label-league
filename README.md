# Label League

## What this is

Label League is a 90-day prediction league over Spotify monthly listener growth, where players sign artists during a 14-day window and are scored on weighted log-growth of their roster.

## Stack

- Next.js 15 with App Router
- React 19
- TypeScript
- Tailwind CSS
- shadcn/ui
- Supabase
- Zod
- ESLint
- Prettier
- pnpm

## Local dev

1. Clone the repository.
2. Copy `.env.local.example` to `.env.local`.
3. Fill in the required values in `.env.local`.
4. Run `pnpm install`.
5. Run `pnpm dev`.
6. Run the pipeline: `cd scripts/pipeline && pip install -r requirements.txt && python run_daily.py`
