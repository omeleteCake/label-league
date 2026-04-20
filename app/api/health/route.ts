import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";

export async function GET() {
  try {
    await createClient();
    await pingSupabaseHealth();

    return NextResponse.json({
      ok: true,
      supabase: "connected",
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        supabase: "error",
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 503 },
    );
  }
}

async function pingSupabaseHealth() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl) {
    throw new Error("Missing NEXT_PUBLIC_SUPABASE_URL");
  }

  if (!supabaseAnonKey) {
    throw new Error("Missing NEXT_PUBLIC_SUPABASE_ANON_KEY");
  }

  const response = await fetch(new URL("/auth/v1/health", supabaseUrl), {
    headers: {
      apikey: supabaseAnonKey,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Supabase health ping failed with status ${response.status}`);
  }
}
