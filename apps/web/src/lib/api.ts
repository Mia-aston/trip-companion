import type { Trip, TripCreate } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export async function createTrip(input: TripCreate): Promise<Trip> {
  const response = await fetch(`${API_BASE}/trips`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(`createTrip failed: ${response.status}`);
  return response.json();
}
