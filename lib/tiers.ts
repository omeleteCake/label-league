import type { Tier } from "@/lib/types/database";

export const TIER_THRESHOLDS = {
  underground: 10000,
  rising: 100000,
  emerging: 1000000,
  established: 10000000,
} as const;

export const TIER_ORDER = ["underground", "rising", "emerging", "established"] as const;

export function getTier(listeners: number): Tier | null {
  if (listeners < TIER_THRESHOLDS.underground) {
    return null;
  }

  if (listeners < TIER_THRESHOLDS.rising) {
    return "underground";
  }

  if (listeners < TIER_THRESHOLDS.emerging) {
    return "rising";
  }

  if (listeners < TIER_THRESHOLDS.established) {
    return "emerging";
  }

  return "established";
}

export function getMinSlotsForTier(tier: Tier): number {
  switch (tier) {
    case "underground":
      return 1;
    case "rising":
      return 2;
    case "emerging":
      return 3;
    case "established":
      return 5;
  }
}

export function tiersCrossed(from: Tier, to: Tier): number {
  const fromIndex = TIER_ORDER.indexOf(from);
  const toIndex = TIER_ORDER.indexOf(to);

  return Math.max(0, toIndex - fromIndex);
}
