import type { ApiError, Trip, TripCreate } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class ApiRequestError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ApiError | null,
  ) {
    super(body?.error.message ?? `API request failed: ${status}`);
  }
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
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
