# Web app

Next.js 16 (App Router) + TypeScript. Talks to the API only through `src/lib/api.ts`; contract types are generated (`src/types/api.gen.ts`, A-08).

## Screens (M1)
| Route | What |
|---|---|
| `/` | Create Trip form: title, origin, dates, multi-city stops (live "n of N nights allocated"), travellers (adults, children ages, infants), mobility, currency, budget, pace, interests, dietary. API validation errors are shown inline. |
| `/trips/[id]` | Read-only trip page: overview, stops, members, constraints, bookings. Instants are shown in the stop's timezone (A-11). |
| `/trips/[id]/flights` | Flight picker (UI-004): outbound / return search (IATA, date, stops, bags, sort; defaults from the trip), offers with local times (+1), stops, duration, bags, "price held ~N min", Select → tentative booking + affected days + re-plan link, "Book on provider ↗"; 409 clears stale offers. |
| `/trips/[id]/itinerary` | Itinerary editor (UI-002): generate / re-plan, version + reason + diff summary, warnings, per day: items with local times (+1 for next day), lock / unlock / remove, add item, "Re-plan this day" (pace, stay near centre, drop your items, reason). Validator errors shown inline; nothing changes on error. |

Later screens (per ROADMAP): place drawer Know/Eat/Photo/Practical (M5), budget & settlement (M6), Today (M7).

## Run locally
```bash
npm ci
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev      # API must be running (see root README)
```

## Checks
```bash
npm run typecheck
npm run gen:types          # after an API contract change; commit api.gen.ts
npm run build && npm run e2e   # Playwright, desktop + phone; starts API + web, needs DATABASE_URL (migrated PostGIS)
```
