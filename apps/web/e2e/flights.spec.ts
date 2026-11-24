import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

// UI-004: golden slice E4 through the flight picker.

const EGYPT = JSON.parse(readFileSync(join(__dirname, "../../../services/api/tests/fixtures/egypt/trip_create.json"), "utf8"));

test("E4: pick an earlier arrival, see the affected day, re-plan link", async ({ page, request }) => {
  const trip = await (await request.post("http://localhost:8000/v1/trips", { data: EGYPT })).json();
  await page.goto(`/trips/${trip.id}`);
  await page.getByRole("link", { name: "Flights →" }).click();

  const outbound = page.getByRole("region", { name: "Outbound flight" });
  await expect(outbound.getByTestId("current-outbound")).toContainText("Arrival flight to Cairo");
  await outbound.getByLabel("To (IATA)").fill("CAI");
  await outbound.getByRole("button", { name: "Search outbound" }).click();

  await expect(outbound.getByTestId("summary-outbound")).toContainText("2 options for 2 passengers on 31 Oct 2026 · 2 hidden by your filters");
  const offers = outbound.getByTestId("offer");
  await expect(offers).toHaveCount(2);
  await expect(offers.first()).toContainText("16:30 LHR → 23:30 CAI");
  await expect(offers.first()).toContainText("580.00 GBP");
  await expect(offers.nth(1)).toContainText("07:00 LHR → 14:00 CAI");
  await expect(offers.first().getByTestId("expiry")).toContainText("price held");

  await offers.nth(1).getByRole("button", { name: "Select NM780" }).click();
  const done = page.getByTestId("selected");
  await expect(done).toContainText("Added: Nile Mock Air NM780 LHR→CAI — 680.00 GBP · tentative");
  await expect(done).toContainText("Free time changed on 31 Oct 2026");
  await expect(outbound.getByTestId("current-outbound")).toContainText("NM780");
  await expect(outbound.getByTestId("offer")).toHaveCount(0); // results cleared after selecting

  await done.getByRole("link", { name: "Re-plan in the itinerary →" }).click();
  await expect(page).toHaveURL(new RegExp(`/trips/${trip.id}/itinerary$`));
});

test("return search: overnight flight shows +1, filters can be relaxed", async ({ page, request }) => {
  const trip = await (await request.post("http://localhost:8000/v1/trips", { data: EGYPT })).json();
  await page.goto(`/trips/${trip.id}/flights`);
  const back = page.getByRole("region", { name: "Return flight" });
  await back.getByLabel("From (IATA)").fill("LXR");
  await back.getByRole("button", { name: "Search return" }).click();
  await expect(back.getByTestId("offer").filter({ hasText: "NM315" })).toContainText("22:30 LXR → 03:00 +1 LGW");

  await back.getByLabel("Checked bags").selectOption("0");
  await back.getByRole("button", { name: "Search return" }).click();
  await expect(back.getByTestId("offer").first()).toContainText("BM695"); // cheapest once bags are not required
});

test("invalid airports show the API error", async ({ page, request }) => {
  const trip = await (await request.post("http://localhost:8000/v1/trips", { data: EGYPT })).json();
  await page.goto(`/trips/${trip.id}/flights`);
  const outbound = page.getByRole("region", { name: "Outbound flight" });
  await outbound.getByLabel("To (IATA)").fill("LON");
  await outbound.getByRole("button", { name: "Search outbound" }).click();
  await expect(outbound.getByRole("alert")).toContainText("from and to airports must differ");
});
