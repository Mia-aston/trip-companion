# Decisions

Changing an architecture/product assumption requires an entry here **before** code continues.
Accepted long-form ADRs live in `docs/decisions/`.

## Accepted
| ID | Decision | Ref |
|---|---|---|
| ADR-0001 | Modular monorepo (web + API + docs), modular monolith API | `decisions/0001-monorepo.md` |
| A-02 | PostgreSQL 16 + PostGIS; `geography(Point,4326)` for places; Alembic migrations with deterministic constraint names | migration 0001 |
| A-03 | Split docs in `docs/` are the source of truth; plan v0.1 archived in `docs/archive/` | this PR |
| A-04 | Scope tiers MVP / NICE / NEXT / NO with change rule | `SCOPE.md` |

## Open (default applies until decided)
| ID | Decision needed | Default until decided | Needed by |
|---|---|---|---|
| D-01 | Auth provider | simple email/OAuth abstraction; domain not bound to vendor; M1 runs single-user dev auth | M1 (stub), M8 (real) |
| D-02 | Map rendering + places provider (Google Places New?) | map rendering separate from place data adapter; verify EEA terms before production | M2 live adapter |
| D-03 | Live flight provider for MVP (Skyscanner vs Duffel) | mock adapter; choose after access/cost check | M4 live adapter |
| D-04 | Vector search (pgvector) | not added until semantic retrieval clearly beats relational filters | M5 |
| D-05 | Photo spot sourcing | curated only; user submissions after a moderation flow exists (NEXT) | M5 |
| D-06 | FX source | provider adapter; finalized expenses may freeze the historical rate | M6 |
| D-07 | LLM provider + structured output mechanism | provider-agnostic `Planner` interface; fake planner in tests | M3 |
| D-08 | TS contracts: hand-written vs generated | generate TS types from FastAPI OpenAPI (replaces `packages/contracts/`) | M0 (CORE-001) |
| D-09 | Settlement formula sign | `net = paid - share + sent - received` (plan v0.1 had transfer signs reversed) | M6 — owner to confirm |
| D-10 | Egypt fixture dates/details | draft in `TESTING.md` (31 Oct – 6 Nov 2026) | M1 — owner to confirm |
| D-11 | Members vs travellers | separate: `adults/children/infants` drive planning & fares; `members` drive money | M0 — owner to confirm |
| D-12 | Supported UI/content languages for MVP | en + vi | M5 |
