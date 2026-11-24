# Testing strategy & gates

Source: plan v0.1 §16, §23. Process: `docs/WORKFLOW.md`.

> **Build gate:** a feature is not done because a model produced nice output. It must pass deterministic validators and tests.

## Test layers

| Layer | What | Where | Runs | From |
|---|---|---|---|---|
| Unit | split formulas, score functions, time-window validator, lock rules | `tests/test_*.py` | every PR | M0 ✅ |
| Contract | provider fixture → normalized model; every adapter passes the same suite | `tests/test_providers_contract.py` + `tests/fixtures/` | every PR | M0 ✅ |
| Schema / DB | migrations up/down, constraints, cascades, PostGIS | `tests/db/` (needs `TEST_DATABASE_URL`) | every PR (CI PostGIS) | M0 ✅ |
| API | route validation + persistence via TestClient | `tests/test_trips_api.py`, `tests/db/test_trips_api.py` | every PR | M1 ✅ |
| Property-based | validator reports overlap iff present; GreedyPlanner output never has validator errors (random pace/interests/mobility/bookings/must-dos) ✅ · splits sum to expense; settlement Σ = 0 (M6) | `tests/test_itinerary_properties.py` (`hypothesis`) | every PR | M3 ✅ / M6 |
| Golden scenario | Egypt slices (below) | `tests/golden/` | every PR touching itinerary/budget | M1→M6 |
| Evals | itinerary feasibility rate, explanation grounding, food-match explanation grounding | `evals/` (LLM, not in default CI) | nightly / manual | M3/M5 |
| UI | create trip ✅, edit day + E3 in the editor ✅, choose flight + E4 ✅, add expense (Playwright, desktop + phone) | `apps/web/e2e/` | every PR (CI `e2e` job) | M1 ✅ · M3 ✅ · M4 ✅ → M7 |

Rules:
- No live provider calls in CI. Live adapters are tested with sanitized recorded fixtures.
- LLM calls in tests are replaced by a deterministic fake planner that returns fixture JSON; the validator is always real.
- Each bug fix adds a failing test first.

## Gates (where tests sit in the workflow)

| Gate | When | Must pass |
|---|---|---|
| **G0 Doc gate** | before an issue is started | issue has tier, milestone, acceptance criteria, contract reference; touched contracts updated in docs |
| **G1 Contract gate** | contract PR (models/schemas/fixtures, no logic) | types compile, fixtures validate against models, new tests exist (may be `xfail`) |
| **G2 PR gate** (CI) | every PR | ruff + format, `alembic check`, unit/contract/DB/API tests, web typecheck; PR < ~400 changed lines |
| **G3 Milestone exit** | end of milestone | milestone exit criterion test is green (golden slice), no open MVP issue, AI_HANDOFF updated |
| **G4 Release gate** (M8) | staging | all golden scenarios + failure-mode tests (provider down, stale data, expired fare) on staging |

## Golden scenario: Egypt

Fixture: `tests/fixtures/egypt/` (built in M1, extended per milestone). Confirmed by owner (A-06).

| Item | Value |
|---|---|
| Members | Mia, QA (2 adults) — base/settlement currency GBP |
| Arrival | 31 Oct 2026, 23:30 Cairo (CAI) — late arrival, sleep only |
| 1–2 Nov | Cairo / Giza (must-do: Giza pyramids — locked) |
| 3 Nov | Western Desert overnight (booking: desert camp) |
| 4 Nov | Transfer to Luxor (booking: train/railway £101.56, payer Mia) |
| 5 Nov | Luxor west bank; 05:30 balloon (weather_sensitive, $150, payer QA) |
| 6 Nov | Originally Aswan day trip → **changed to Luxor downtown** |
| Departure | 6 Nov 2026, 22:30 from Luxor (LXR); collect bags 20:30 |
| Hotel | The View Hotel Luxor, 4–6 Nov (€128.62, payer QA) |

| Slice | Milestone | Assertion |
|---|---|---|
| E1 persist | M1 | Egypt trip with members, stops, constraints, bookings saves and reloads identically, no AI |
| E2 feasibility ✅ (`tests/golden/test_e2_day_candidates.py`; API level in `tests/db/test_places_api.py`) | M2 | each day's candidates are reachable within the day window using the route matrix; late-arrival day has 0 sightseeing stops |
| E3 regenerate ✅ `tests/db/test_golden_e3.py` (v1 generated; user adds custom item "Aswan day trip" 08:00–19:00 on 6 Nov → v2; regenerate 6 Nov with `remove_item_keys=[aswan]`, `stay_within_m=3000` → v3) | M3 | "remove Aswan, stay Luxor downtown" on 6 Nov changes only 6 Nov items; all other days, hotel and flight are byte-identical; new plan_version with diff; validator passes; 22:30 departure respected |
| E3b weather ✅ | M3 | balloon booking set to `cancelled`, regenerate 5 Nov → only the 05:30–08:00 block changes; other 5 Nov locked items stay |
| E4 flights ✅ `tests/db/test_golden_e4.py` | M4 | select an outbound landing 31 Oct 23:30 → 31 Oct capacity 0; switch to one landing 14:00 → 31 Oct capacity > 0 with candidates; expired offer → 409, trip unchanged |
| E5 recommendations | M5 | Luxor downtown lunch ranks by taste profile; every result has provenance + why; no sensitive inference |
| E6 settlement | M6 | Egypt expense case reconciles; transfers excluded from trip cost; Σ net = 0 |
| E7 today | M7 | on 6 Nov, "running late 60 min" shifts only unlocked items after now; departure untouched |

## Failure-mode tests (M8, some earlier)
- provider timeout → 503 with stale data + label, no fabricated results
- expired flight offer → re-search required before select
- LLM returns invalid / conflicting plan → validator rejects, plan_version not written
- FX provider down → last known rate with `as_of` shown
