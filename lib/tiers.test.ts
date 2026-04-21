import { describe, expect, it } from "vitest";

import { getMinSlotsForTier, getTier, tiersCrossed } from "./tiers";

describe("getTier", () => {
  it("returns null below the listener floor", () => {
    expect(getTier(0)).toBeNull();
    expect(getTier(9999)).toBeNull();
  });

  it("returns underground at the underground bounds", () => {
    expect(getTier(10000)).toBe("underground");
    expect(getTier(50000)).toBe("underground");
    expect(getTier(99999)).toBe("underground");
  });

  it("returns rising at the rising bounds", () => {
    expect(getTier(100000)).toBe("rising");
    expect(getTier(999999)).toBe("rising");
  });

  it("returns emerging at the emerging bounds", () => {
    expect(getTier(1000000)).toBe("emerging");
    expect(getTier(9999999)).toBe("emerging");
  });

  it("returns established at and above the established threshold", () => {
    expect(getTier(10000000)).toBe("established");
    expect(getTier(100000000)).toBe("established");
  });
});

describe("getMinSlotsForTier", () => {
  it("returns the minimum slot count for each tier", () => {
    expect(getMinSlotsForTier("underground")).toBe(1);
    expect(getMinSlotsForTier("rising")).toBe(2);
    expect(getMinSlotsForTier("emerging")).toBe(3);
    expect(getMinSlotsForTier("established")).toBe(5);
  });
});

describe("tiersCrossed", () => {
  it("returns 0 for the same tier", () => {
    expect(tiersCrossed("underground", "underground")).toBe(0);
    expect(tiersCrossed("rising", "rising")).toBe(0);
    expect(tiersCrossed("emerging", "emerging")).toBe(0);
    expect(tiersCrossed("established", "established")).toBe(0);
  });

  it("returns 0 for downward moves", () => {
    expect(tiersCrossed("rising", "underground")).toBe(0);
    expect(tiersCrossed("emerging", "rising")).toBe(0);
    expect(tiersCrossed("established", "underground")).toBe(0);
  });

  it("returns the number of upward tier boundaries crossed", () => {
    expect(tiersCrossed("underground", "rising")).toBe(1);
    expect(tiersCrossed("underground", "emerging")).toBe(2);
    expect(tiersCrossed("underground", "established")).toBe(3);
    expect(tiersCrossed("rising", "established")).toBe(2);
    expect(tiersCrossed("emerging", "established")).toBe(1);
  });
});
