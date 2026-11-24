# Manual testing (local stack)

Everything runs on **mock providers** (places, routes, flights) — no API keys, no real bookings.

## Start
Requires Docker Desktop (or Docker Engine + Compose v2).

```bash
git clone https://github.com/Mia-aston/trip-companion.git
cd trip-companion
docker compose up --build
```

First build takes a few minutes. When the logs show `Egypt demo trip: http://localhost:3000/trips/2773c62e-e3ed-5928-801e-e1b0f8102a39`, open:

- App: http://localhost:3000
- Demo trip (Egypt): http://localhost:3000/trips/2773c62e-e3ed-5928-801e-e1b0f8102a39
- API docs (Swagger): http://localhost:8000/docs

Stop with `Ctrl+C`. Reset all data: `docker compose down -v`. Reset only the demo trip: `docker compose exec api python scripts/seed_egypt.py --reset`.

## Checklist
Tick what works; note anything odd (screenshot + steps) in a GitHub issue.

### 1. Create a trip (M1)
- [ ] Home → fill title, from, dates; add 2 stops; the "n of N nights allocated" hint turns green when it matches.
- [ ] Children ages / infants change the traveller count on the trip page.
- [ ] Wrong nights total → the API error is shown on the form; nothing is created.
- [ ] Reload the trip page → same data (it comes from the database).

### 2. Itinerary (M3) — on the demo trip
- [ ] "Open itinerary →" → **Generate itinerary** → version 1; 31 Oct has only the arrival flight (late arrival); 6 Nov ends before 19:30 (airport).
- [ ] Each place has a "why" line; Giza Pyramids is on a Cairo day (must-do).
- [ ] Lock a visit → "locked" tag, Remove disabled; Unlock → Remove works; each step makes a new version.
- [ ] **E3:** on 6 Nov "Add item" `Aswan day trip` 08:00–19:00 → version 2. "Re-plan this day": stay within 3 km, relaxed, tick "Aswan day trip", reason → version 3: only 6 Nov changed (summary line), the 22:30 departure is still there, other days identical.
- [ ] Add an item on 31 Oct 20:00–21:00 → V1 error shown, version unchanged.

### 3. Flights (M4) — on the demo trip
- [ ] "Flights →" → Outbound: To `CAI` → Search → 2 options (16:30→23:30 £580, 07:00→14:00 £680), "2 hidden by your filters".
- [ ] Checked bags "Not needed" → the cheaper 1-stop via IST appears; Sort "Fastest" puts it last.
- [ ] **E4:** Select the 07:00→14:00 flight → banner "Free time changed on 31 Oct" → "Re-plan in the itinerary" → Re-plan whole trip → 31 Oct now has visits from ~15:30.
- [ ] Return: From `LXR` → the 22:30 flight shows `03:00 +1`.
- [ ] Wait > 30 minutes after a search, then Select → "Offer expired — search again".

### 4. Phone
- [ ] Repeat 2 and 3 on a phone-width browser window (or DevTools device mode): no sideways scrolling, buttons reachable.

## Known limits (by design, see SCOPE/DECISIONS)
No login (anyone on your machine sees all trips) · no trips list page yet (use the demo URL or the URL after creating) · no editing of trip fields/bookings in the UI (API only) · mock data only (D-02/D-03 pending) · one-day regenerate, no free-text interpretation (A-20).
