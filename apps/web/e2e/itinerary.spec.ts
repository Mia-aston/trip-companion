import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

// UI-002: golden slice E3 through the editor — generate, add "Aswan day trip", re-plan 6 Nov near the centre.

const EGYPT = JSON.parse(readFileSync(join(__dirname, "../../../services/api/tests/fixtures/egypt/trip_create.json"), "utf8"));

test("E3 in the editor: only 6 Nov changes", async ({ page, request }) => {
  const trip = await (await request.post("http://localhost:8000/v1/trips", { data: EGYPT })).json();
  await page.goto(`/trips/${trip.id}`);
  await page.getByRole("link", { name: "Open itinerary →" }).click();
  await expect(page.getByText("No itinerary yet.")).toBeVisible();

  await page.getByRole("button", { name: "Generate itinerary" }).click();
  await expect(page.getByTestId("version")).toContainText("Version 1");
  const nov6 = page.getByTestId("day-2026-11-06");
  await expect(nov6.getByText("Departure flight from Luxor")).toBeVisible();
  await expect(nov6.getByTestId("plan-item").filter({ hasText: "Departure flight" })).toContainText("22:30–05:00 +1");
  const nov1Before = await page.getByTestId("day-2026-11-01").innerText();

  // v2: add the Aswan day trip
  await nov6.getByRole("button", { name: "Add item" }).click();
  await nov6.getByLabel("Title").fill("Aswan day trip");
  await nov6.getByLabel("Start").fill("08:00");
  await nov6.getByLabel("End").fill("19:00");
  await nov6.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByTestId("version")).toContainText("Version 2");
  await expect(nov6.getByText("Aswan day trip")).toBeVisible();

  // v3: drop it and stay within 3 km
  await nov6.getByRole("button", { name: "Re-plan this day" }).click();
  await nov6.getByLabel("Stay near the centre").selectOption("3000");
  await nov6.getByLabel("Pace").selectOption("relaxed");
  await nov6.getByLabel("Reason (saved with the version)").fill("Remove Aswan; stay around Luxor downtown");
  await nov6.getByRole("checkbox", { name: "Aswan day trip" }).check();
  await nov6.getByRole("button", { name: /Re-plan Fri 6 Nov/ }).click();

  await expect(page.getByTestId("version")).toContainText("Version 3 · planned (greedy) · Remove Aswan; stay around Luxor downtown");
  await expect(page.getByTestId("diff-summary")).toContainText("6 Nov 2026");
  await expect(page.getByTestId("diff-summary")).not.toContainText("1 Nov 2026");
  await expect(nov6.getByText("Aswan day trip")).toHaveCount(0);
  await expect(nov6.getByText("Departure flight from Luxor")).toBeVisible();
  expect(await page.getByTestId("day-2026-11-01").innerText()).toBe(nov1Before);
});

test("lock, unlock and remove; bookings have no actions", async ({ page, request }) => {
  const trip = await (await request.post("http://localhost:8000/v1/trips", { data: EGYPT })).json();
  await request.post(`http://localhost:8000/v1/trips/${trip.id}/itinerary/generate`, { data: {} });
  await page.goto(`/trips/${trip.id}/itinerary`);

  const day = page.getByTestId("day-2026-11-05");
  const first = day.getByTestId("plan-item").filter({ hasText: "Luxor Temple" });
  await first.getByRole("button", { name: "Lock Luxor Temple" }).click();
  await expect(page.getByTestId("version")).toContainText("Version 2 · your edit · Locked 'Luxor Temple'");
  await expect(first.getByRole("button", { name: "Remove Luxor Temple" })).toBeDisabled();
  await first.getByRole("button", { name: "Unlock Luxor Temple" }).click();
  await first.getByRole("button", { name: "Remove Luxor Temple" }).click();
  await expect(page.getByTestId("version")).toContainText("Version 4");
  await expect(day.getByText("Luxor Temple")).toHaveCount(0);

  const balloon = day.getByTestId("plan-item").filter({ hasText: "Hot air balloon" });
  await expect(balloon.getByRole("button")).toHaveCount(0);
});

test("validator errors are shown and nothing changes", async ({ page, request }) => {
  const trip = await (await request.post("http://localhost:8000/v1/trips", { data: EGYPT })).json();
  await request.post(`http://localhost:8000/v1/trips/${trip.id}/itinerary/generate`, { data: {} });
  await page.goto(`/trips/${trip.id}/itinerary`);
  const day = page.getByTestId("day-2026-10-31"); // late arrival: no free time
  await day.getByRole("button", { name: "Add item" }).click();
  await day.getByLabel("Title").fill("Night walk");
  await day.getByLabel("Start").fill("20:00");
  await day.getByLabel("End").fill("21:00");
  await day.getByRole("button", { name: "Add", exact: true }).click();
  const alert = page.getByRole("alert").filter({ hasText: "Plan failed validation" });
  await expect(alert).toContainText("V1");
  await expect(page.getByTestId("version")).toContainText("Version 1");
});
