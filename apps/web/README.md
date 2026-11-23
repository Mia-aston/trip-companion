# Web app

Next.js 16 (App Router) + TypeScript. Talks to the API only through `src/lib/api.ts`; contract types are generated (`src/types/api.gen.ts`, A-08).

## Screens (M1)
| Route | What |
|---|---|
| `/` | Create Trip form: title, origin, dates, multi-city stops (live "n of N nights allocated"), travellers (adults, children ages, infants), mobility, currency, budget, pace, interests, dietary. API validation errors are shown inline. |
| `/trips/[id]` | Read-only trip page: overview, stops, members, constraints, bookings. Instants are shown in the stop's timezone (A-11). |

Later screens (per ROADMAP): flight options (M4), itinerary editor (M3), place drawer Know/Eat/Photo/Practical (M5), budget & settlement (M6), Today (M7).

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
