# Pipeline

## What this is

This directory contains the shared infrastructure for Label League's Python data pipeline, including configuration, structured logging, Supabase admin access, and Spotify API authentication helpers that future fetch, scrape, and orchestration scripts will reuse.

## Setup

Install the pipeline dependencies from the repository root or from this directory:

```bash
python -m pip install -r scripts/pipeline/requirements.txt
```

Create `.env.local` at the project root and fill in `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SPOTIFY_CLIENT_ID`, and `SPOTIFY_CLIENT_SECRET`.

## Running

No fetching, scraping, or orchestration scripts exist yet. Future scripts should be invoked from the repository root with `python scripts/pipeline/<script>.py` or from this directory with `python <script>.py`.

## Why we scrape

Spotify monthly listener count is not available from the Spotify Web API, so listener counts come from parsing `open.spotify.com/artist/{id}` pages. That approach is fragile because public page structure can change without notice, and production-grade data should eventually come from a dedicated provider such as Songstats or Chartmetric.
