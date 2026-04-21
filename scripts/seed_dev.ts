import { createClient } from "@supabase/supabase-js";
import { config } from "dotenv";

import type { Tier } from "@/lib/types/database";

config({ path: ".env.local", quiet: true });

type SeedArtist = {
  spotifyId: string;
  name: string;
  genres: string[];
  tier: Tier;
  currentListeners: number;
  trendPercent: number;
};

type InsertedArtist = {
  id: string;
  spotify_id: string;
};

const ZERO_UUID = "00000000-0000-0000-0000-000000000000";

const TABLES_TO_CLEAR = [
  "audit_log",
  "opt_out_requests",
  "badges",
  "season_scores",
  "signings",
  "rosters",
  "listener_snapshots",
  "seasons",
  "artists",
] as const;

const SEED_ARTISTS: SeedArtist[] = [
  {
    spotifyId: "seed_artist_001",
    name: "Quiet Static",
    genres: ["indie", "electronic"],
    tier: "underground",
    currentListeners: 15000,
    trendPercent: 0.08,
  },
  {
    spotifyId: "seed_artist_002",
    name: "Bluesound Collective",
    genres: ["soul", "jazz"],
    tier: "underground",
    currentListeners: 23000,
    trendPercent: 0.12,
  },
  {
    spotifyId: "seed_artist_003",
    name: "The Glass Lanterns",
    genres: ["folk", "indie"],
    tier: "underground",
    currentListeners: 36000,
    trendPercent: -0.03,
  },
  {
    spotifyId: "seed_artist_004",
    name: "Velvet Circuit",
    genres: ["synthpop", "electronic"],
    tier: "underground",
    currentListeners: 48000,
    trendPercent: 0.02,
  },
  {
    spotifyId: "seed_artist_005",
    name: "North Pier",
    genres: ["rock", "alternative"],
    tier: "underground",
    currentListeners: 64000,
    trendPercent: 0.15,
  },
  {
    spotifyId: "seed_artist_006",
    name: "June Mirage",
    genres: ["dream pop", "indie"],
    tier: "underground",
    currentListeners: 79000,
    trendPercent: 0.05,
  },
  {
    spotifyId: "seed_artist_007",
    name: "Arcade Weather",
    genres: ["pop", "electronic"],
    tier: "rising",
    currentListeners: 150000,
    trendPercent: 0.1,
  },
  {
    spotifyId: "seed_artist_008",
    name: "Saffron Vale",
    genres: ["r&b", "pop"],
    tier: "rising",
    currentListeners: 240000,
    trendPercent: 0.07,
  },
  {
    spotifyId: "seed_artist_009",
    name: "Mineral Bloom",
    genres: ["ambient", "electronic"],
    tier: "rising",
    currentListeners: 380000,
    trendPercent: -0.02,
  },
  {
    spotifyId: "seed_artist_010",
    name: "Paper District",
    genres: ["indie rock", "alternative"],
    tier: "rising",
    currentListeners: 520000,
    trendPercent: 0.13,
  },
  {
    spotifyId: "seed_artist_011",
    name: "Golden Orchard",
    genres: ["country", "folk"],
    tier: "rising",
    currentListeners: 700000,
    trendPercent: 0.04,
  },
  {
    spotifyId: "seed_artist_012",
    name: "Neon Harbor",
    genres: ["dance", "pop"],
    tier: "emerging",
    currentListeners: 2000000,
    trendPercent: 0.11,
  },
  {
    spotifyId: "seed_artist_013",
    name: "Atlas & Ivy",
    genres: ["indie pop", "alternative"],
    tier: "emerging",
    currentListeners: 4700000,
    trendPercent: 0.06,
  },
  {
    spotifyId: "seed_artist_014",
    name: "Midnight Relay",
    genres: ["electronic", "house"],
    tier: "emerging",
    currentListeners: 8000000,
    trendPercent: 0.14,
  },
  {
    spotifyId: "seed_artist_015",
    name: "Avery Sol",
    genres: ["pop", "r&b"],
    tier: "established",
    currentListeners: 50000000,
    trendPercent: 0.03,
  },
];

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl) {
  console.error("Missing required environment variable: NEXT_PUBLIC_SUPABASE_URL");
  process.exit(1);
}

if (!serviceRoleKey) {
  console.error("Missing required environment variable: SUPABASE_SERVICE_ROLE_KEY");
  process.exit(1);
}

const supabase = createClient(supabaseUrl, serviceRoleKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false,
  },
});

function daysFromNow(days: number, now = new Date()): string {
  const date = new Date(now);
  date.setDate(date.getDate() + days);
  return date.toISOString();
}

function buildSnapshots(artistId: string, artist: SeedArtist, now: Date) {
  const startListeners = artist.currentListeners / (1 + artist.trendPercent);

  return Array.from({ length: 30 }, (_, index) => {
    const progress = index / 29;
    const listeners = Math.round(
      startListeners + (artist.currentListeners - startListeners) * progress,
    );

    return {
      artist_id: artistId,
      monthly_listeners: listeners,
      captured_at: daysFromNow(index - 29, now),
    };
  });
}

async function clearSeededTables() {
  for (const table of TABLES_TO_CLEAR) {
    const { error } = await supabase.from(table).delete().neq("id", ZERO_UUID);

    if (error) {
      throw new Error(`Failed to clear ${table}: ${error.message}`);
    }
  }
}

async function insertArtists(): Promise<InsertedArtist[]> {
  const rows = SEED_ARTISTS.map(({ spotifyId, name, genres }) => ({
    spotify_id: spotifyId,
    name,
    image_url: null,
    genres,
  }));

  const { data, error } = await supabase.from("artists").insert(rows).select("id, spotify_id");

  if (error) {
    throw new Error(`Failed to insert artists: ${error.message}`);
  }

  if (!data || data.length !== SEED_ARTISTS.length) {
    throw new Error(
      `Expected ${SEED_ARTISTS.length} inserted artists, received ${data?.length ?? 0}.`,
    );
  }

  return data;
}

async function insertSnapshots(insertedArtists: InsertedArtist[], now: Date): Promise<number> {
  const artistIdsBySpotifyId = new Map(
    insertedArtists.map((artist) => [artist.spotify_id, artist.id] as const),
  );

  const rows = SEED_ARTISTS.flatMap((artist) => {
    const artistId = artistIdsBySpotifyId.get(artist.spotifyId);

    if (!artistId) {
      throw new Error(`Missing inserted artist id for ${artist.spotifyId}.`);
    }

    return buildSnapshots(artistId, artist, now);
  });

  const { error } = await supabase.from("listener_snapshots").insert(rows);

  if (error) {
    throw new Error(`Failed to insert listener snapshots: ${error.message}`);
  }

  return rows.length;
}

async function insertSeason(insertedArtists: InsertedArtist[], now: Date) {
  const artistPool = insertedArtists.map((artist) => artist.id);

  const { error } = await supabase.from("seasons").insert({
    season_number: 1,
    signing_opens_at: daysFromNow(-2, now),
    signing_closes_at: daysFromNow(12, now),
    season_ends_at: daysFromNow(88, now),
    status: "signing",
    artist_pool: artistPool,
  });

  if (error) {
    throw new Error(`Failed to insert season: ${error.message}`);
  }
}

async function main() {
  const now = new Date();

  await clearSeededTables();

  const insertedArtists = await insertArtists();
  const snapshotCount = await insertSnapshots(insertedArtists, now);

  await insertSeason(insertedArtists, now);

  console.log(
    `Seeded ${insertedArtists.length} artists, ${snapshotCount} snapshots, 1 season in signing phase.`,
  );
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error);

  console.error("Dev seed failed:");
  console.error(message);
  process.exit(1);
});
