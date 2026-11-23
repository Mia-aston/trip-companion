import type { Money } from "../types";

/** Show a UTC instant in a stop's IANA timezone (A-11). Falls back to UTC when unknown. */
export function localTime(iso: string, timeZone?: string | null): string {
  const tz = timeZone ?? "UTC";
  const text = new Intl.DateTimeFormat("en-GB", {
    timeZone: tz,
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
  return timeZone ? text : `${text} UTC`;
}

export function shortDate(isoDate: string): string {
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(
    new Date(`${isoDate}T00:00:00Z`),
  );
}

export function money(m: Money): string {
  return `${m.amount} ${m.currency}`;
}
