# Plan v0.1 coverage

Review of `docs/archive/TRIP_COMPANION_PRODUCT_TECH_PLAN_v0.1_full.md` against the repo (23 Nov 2026).
Status **before** this review → where it lives **now**. "Code gap" = docs are complete, implementation is scheduled.

| Plan § | Topic | Before review | Now covered in | Code gap (scheduled) |
|---|---|---|---|---|
| 1 | Executive summary, thesis | partial (PRODUCT core promise) | PRODUCT.md | — |
| 2 | Principles (8) | partial (4 of 8) | PRODUCT.md | — |
| 3 | Users, JTBD, Egypt scenario | **missing** | PRODUCT.md, TESTING.md (fixture + slices E1–E7) | Egypt fixture → M1 |
| 4 | Scope MVP / later / non-goals | **missing** | SCOPE.md (tiers, change rule, per-module table) | — |
| 5 | Before / During / After | covered | PRODUCT.md (tiered) | — |
| 6 | Functional requirements per module | partial | MODULES.md, SCOPE.md | — |
| 7 | Food / knowledge / photo | partial (taste vector only) | PRODUCT.md | TasteVector lacks bitter/smoky/texture → FOOD-001 |
| 8 | Providers | partial (no routing/weather/FX detail) | PROVIDERS.md | — |
| 9 | Safety & privacy | partial (food only) | PRODUCT.md | delete-my-data → M1/M8 |
| 10 | Architecture & layer rules | partial (no layer table, no orchestration) | ARCHITECTURE.md | `app/orchestration/` → M3 |
| 11 | Domain model (19 entities) | 5 entities in migration 0001 | DATA_MODEL.md (all entities, fields, tier, status) | trips/members/expenses changes → CORE-002, BUD-001 |
| 11.1 / 14 | Expense invariants, settlement | partial | DATA_MODEL.md (+ sign fix D-09) | settlement engine → BUD-002 |
| 12 | API contracts | 1 endpoint, no `/v1` | API_CONTRACTS.md (all endpoints, tier, milestone) | `/v1` prefix → CORE-003 |
| 13 | AI orchestration, partial regen | 1 sentence | ARCHITECTURE.md | M3 |
| 15 | Reliability, caching, cost | **missing** | ARCHITECTURE.md | provider_snapshots → M2; tracing → M8 |
| 16 | Testing strategy | **missing** (tests existed, no strategy) | TESTING.md (layers, gates G0–G4) | property tests, golden, evals → M1+ |
| 17 | Environments | **missing** | ARCHITECTURE.md | staging → M8 |
| 18 | Repo & context rules | covered (AGENTS.md) | AGENTS.md, WORKFLOW.md, ARCHITECTURE.md | — |
| 19 | Roadmap M0–M8 + exit criteria | **different** (repo had M0–M6, flights before itinerary, no exit criteria) | ROADMAP.md (realigned to plan order + exit tests) | — |
| 20 | Issue breakdown | **missing** | ROADMAP.md (issues per milestone) | create GitHub issues per milestone |
| 21 | Risks | **missing** | below | — |
| 22 | Open decisions D-01…D-06 | **missing** | DECISIONS.md (+ D-07…D-12 found in review) | — |
| 23 | Definition of Done | partial (AGENTS handoff) | WORKFLOW.md, PR template | — |
| 24 | References | **missing** | PROVIDERS.md | — |

## Issues found in the plan itself
1. **Settlement sign error** (§14): `+ transfers_received - transfers_sent` should be `+ sent - received`. Fixed in DATA_MODEL.md, D-09.
2. **Travellers as one number** is not enough for fares, activities and splits → `adults / children_ages / infants` + separate `members` (SCOPE.md, D-11).
3. **Multi-city** is required by the Egypt scenario but the plan's `trips` had a single destination → `trip_stops`.
4. **`packages/contracts/`** would duplicate types by hand → generate TS from OpenAPI (D-08).
5. **Roadmap order** in the repo put flights (M3) before itinerary; plan puts places/routing/itinerary first so the engine can be built on mocks without waiting for a flight-provider decision — adopted.
6. Plan lists both "MVP: place cards" and "Later: offline / community spots" but no rule for scope creep → SCOPE.md change rule.

## Risks & mitigations (plan §21)
| Risk | Impact | Mitigation |
|---|---|---|
| Provider access/pricing changes | High | adapter interface + mock + contract suite; one live provider per capability |
| Google Maps/Places terms by region | High | presentation/provider boundary; terms review before launch (D-02) |
| LLM hallucinates schedule/facts | High | structured output + retrieval + deterministic validator (G2/G3) |
| Review data too sparse | Medium | first-party feedback + metadata + confidence score |
| Personalization becomes stereotype | High | explicit taste vectors; privacy test in M5 exit |
| Trip edits cascade unpredictably | High | plan versioning + dependency-aware partial regen (E3) |
| FX drift changes historic budgets | Medium | timestamped / frozen rates (D-06) |
| Context overload for AI coding | Medium | module docs, issue scope, handoff, PR < ~400 lines |
| **Scope creep** (added) | High | SCOPE.md tiers + change rule; WIP = 1 milestone |
