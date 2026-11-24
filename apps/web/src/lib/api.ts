import type { AddItem, ApiError, EditItem, PlanVersion, RegenerateRequest, Trip, TripCreate } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class ApiRequestError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ApiError | null,
  ) {
    super(body?.error.message ?? `API request failed: ${status}`);
  }

  /** Human-readable lines from the error envelope's details. */
  get details(): string[] {
    return (this.body?.error.details ?? []).map((d) => {
      if (typeof d === "string") return d;
      const item = d as { loc?: (string | number)[]; msg?: string; rule?: string; message?: string; date?: string };
      if (item.rule) return `${item.rule}${item.date ? ` (${item.date})` : ""}: ${item.message}`; // validator violation
      const where = (item.loc ?? []).filter((p) => p !== "body").join(".");
      return where ? `${where}: ${item.msg}` : String(item.msg ?? JSON.stringify(d));
    });
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...init.headers },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiError | null;
    throw new ApiRequestError(response.status, body);
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}

export function createTrip(input: TripCreate): Promise<Trip> {
  return request<Trip>("/v1/trips", { method: "POST", body: JSON.stringify(input) });
}

export function getTrip(id: string): Promise<Trip> {
  return request<Trip>(`/v1/trips/${encodeURIComponent(id)}`);
}

// --- itinerary (M3) ---------------------------------------------------------

const itinerary = (tripId: string) => `/v1/trips/${encodeURIComponent(tripId)}/itinerary`;

/** Latest (or a specific) plan version; null when the trip has no itinerary yet. */
export async function getItinerary(tripId: string, version?: number): Promise<PlanVersion | null> {
  try {
    return await request<PlanVersion>(`${itinerary(tripId)}${version ? `?version=${version}` : ""}`);
  } catch (err) {
    if (err instanceof ApiRequestError && err.status === 404) return null;
    throw err;
  }
}

export function generateItinerary(tripId: string, note = ""): Promise<PlanVersion> {
  return request<PlanVersion>(`${itinerary(tripId)}/generate`, { method: "POST", body: JSON.stringify({ note }) });
}

export function regenerateDay(tripId: string, body: RegenerateRequest): Promise<PlanVersion> {
  return request<PlanVersion>(`${itinerary(tripId)}/regenerate`, { method: "POST", body: JSON.stringify(body) });
}

export function addItem(tripId: string, body: AddItem): Promise<PlanVersion> {
  return request<PlanVersion>(`${itinerary(tripId)}/items`, { method: "POST", body: JSON.stringify(body) });
}

export function editItem(tripId: string, itemKey: string, body: EditItem): Promise<PlanVersion> {
  return request<PlanVersion>(`${itinerary(tripId)}/items/${itemKey}`, { method: "PATCH", body: JSON.stringify(body) });
}

export function deleteItem(tripId: string, itemKey: string): Promise<PlanVersion> {
  return request<PlanVersion>(`${itinerary(tripId)}/items/${itemKey}`, { method: "DELETE" });
}

export function lockItem(tripId: string, itemKey: string, locked: boolean): Promise<PlanVersion> {
  return request<PlanVersion>(`${itinerary(tripId)}/items/${itemKey}/lock`, { method: "POST", body: JSON.stringify({ locked }) });
}
