import type { DietaryRestriction, Interest, MobilityNeeds, Pace } from "../types";

// Values must match the API enums; `satisfies` makes tsc reject typos against the generated types.
export const INTERESTS = ["history", "food", "photo", "nature", "nightlife", "shopping", "art", "adventure"] as const satisfies readonly Interest[];
export const DIETARY = [
  "vegetarian",
  "vegan",
  "halal",
  "kosher",
  "gluten_free",
  "lactose_free",
  "nut_allergy",
  "shellfish_allergy",
] as const satisfies readonly DietaryRestriction[];
export const PACES = ["relaxed", "balanced", "packed"] as const satisfies readonly Pace[];
export const MOBILITY = ["none", "limited_walking", "wheelchair", "stroller"] as const satisfies readonly MobilityNeeds[];

export const label = (value: string) => value.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

export function nightsBetween(start: string, end: string): number | null {
  if (!start || !end) return null;
  const ms = Date.parse(`${end}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`);
  return Number.isFinite(ms) ? Math.round(ms / 86_400_000) : null;
}
