# AI handoff log

## Current state (23 Nov 2026)

**Milestone:** M0 — Documentation & contracts (in progress). Branch `m0-foundation`.
**Rule:** no feature code until M0 exit (docs frozen by owner + CORE-001 contracts reviewed).

### Done
- Monorepo scaffold; FastAPI skeleton; mock flight/places providers; taste-match + expense primitives.
- Migration `0001`: trips, trip_members, places (PostGIS), expenses, expense_shares, transfers + constraints. `TripRepository`.
- Tests: unit, provider contract suite, API validation, PostGIS schema tests (35 passing). CI on GitHub Actions.
- Plan v0.1 reviewed and split into repo docs: SCOPE, PRODUCT, ARCHITECTURE, DATA_MODEL, API_CONTRACTS, TESTING, WORKFLOW, DECISIONS, PROVIDERS, PLAN_COVERAGE. Originals in `docs/archive/`.

### Contracts affected
- Docs only. Planned contract changes (not yet in code): Trip variables (adults/children/infants, stops, currencies, budget, day window, mobility), `/v1` prefix, expense field renames. See DATA_MODEL.md status column.

### Known gaps / blockers
- Owner must confirm D-09 (settlement sign), D-10 (Egypt fixture dates), D-11 (members vs travellers) and freeze docs (DOC-001).
- `POST /trips` does not persist; current `Trip` model has single `travellers` field (to change in CORE-001).

### Next safe tasks
1. DOC-001 owner review of `docs/` → mark decisions accepted.
2. CORE-001: shared contracts (`Money`, `Provenance`, `TimeWindow`, …) + new `TripCreate`/`Trip`/`Member`/`Stop`/`Constraint`/`Booking` Pydantic models + OpenAPI → TS type generation. Contract PR only (G1).
3. Then M1 per ROADMAP.md.

### Context rule
Pick one issue, read `AGENTS.md` → `docs/SCOPE.md` → module README → touched contracts. Do not redesign unrelated modules.
