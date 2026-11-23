import { expect, test } from "@playwright/test";

// UI-001 smoke: create a trip through the form, land on its page, see what was saved.

test("create a multi-stop trip and view it", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Title").fill("Hanoi & Da Lat");
  await page.getByLabel("From").fill("SGN");
  await page.getByLabel("Start date").fill("2027-02-10");
  await page.getByLabel("End date").fill("2027-02-15");
  await page.getByLabel("City 1").fill("Hanoi");
  await page.getByLabel("Nights").first().fill("3");
  await page.getByRole("button", { name: "Add stop" }).click();
  await page.getByLabel("City 2").fill("Da Lat");
  await page.getByLabel("Nights").nth(1).fill("2");
  await expect(page.getByTestId("nights-hint")).toHaveText("5 of 5 nights allocated");

  await page.getByLabel("Adults").fill("2");
  await page.getByLabel("Children ages (comma-separated)").fill("7");
  await page.getByLabel("Currency").fill("VND");
  await page.getByLabel("Food").check();
  await page.getByLabel("Vegetarian").check();
  await page.getByRole("button", { name: "Create trip" }).click();

  await expect(page).toHaveURL(/\/trips\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: "Hanoi & Da Lat" })).toBeVisible();
  await expect(page.getByTestId("travellers")).toContainText("3 (2 adults, 1 child (7))");
  const stops = page.getByRole("table", { name: "Stops" });
  await expect(stops.getByRole("row")).toHaveCount(3);
  await expect(stops).toContainText("Da Lat");
  await expect(stops).toContainText("15 Feb 2027");

  // Reload: data comes back from the database, not client state.
  await page.reload();
  await expect(page.getByRole("heading", { name: "Hanoi & Da Lat" })).toBeVisible();
  await expect(page.getByText("Vegetarian")).toBeVisible();
});

test("API validation errors are shown", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Title").fill("Mismatch");
  await page.getByLabel("From").fill("LON");
  await page.getByLabel("Start date").fill("2027-03-01");
  await page.getByLabel("End date").fill("2027-03-04");
  await page.getByLabel("City 1").fill("Rome");
  await page.getByLabel("Nights").first().fill("2");
  await expect(page.getByTestId("nights-hint")).toHaveText("2 of 3 nights allocated");
  await page.getByRole("button", { name: "Create trip" }).click();

  // Next.js renders its own (empty) role=alert route announcer, so match ours by text.
  const alert = page.getByRole("alert").filter({ hasText: "Request validation failed" });
  await expect(alert).toBeVisible();
  await expect(alert).toContainText("stop nights must sum to the trip length (3 nights)");
  await expect(page).toHaveURL("/");
});

test("unknown trip shows not found", async ({ page }) => {
  await page.goto("/trips/00000000-0000-0000-0000-000000000000");
  await expect(page.getByRole("alert").filter({ hasText: "Trip not found." })).toBeVisible();
});

test("times are shown in the stop's local timezone", async ({ page, request }) => {
  const trip = await (
    await request.post("http://localhost:8000/v1/trips", {
      data: {
        title: "TZ check",
        origin: "LON",
        start_date: "2026-11-05",
        end_date: "2026-11-06",
        base_currency: "GBP",
        stops: [{ city: "Luxor", nights: 1, timezone: "Africa/Cairo" }],
        constraints: [
          { kind: "time_window", label: "Collect bags", starts_at: "2026-11-06T20:30:00+02:00", ends_at: "2026-11-06T21:00:00+02:00" },
        ],
      },
    })
  ).json();
  await page.goto(`/trips/${trip.id}`);
  await expect(page.getByText("Collect bags: Fri 6 Nov, 20:30 – Fri 6 Nov, 21:00")).toBeVisible();
});
