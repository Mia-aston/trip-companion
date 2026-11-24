# Trip Companion

A modular travel-planning workspace that turns dates, origin, destination, budget and preferences into an editable trip plan, then enriches it with live transport, places, food, learning cards, photo spots, practical guidance and expense settlement.

## Product loop

`Discover → Search → Plan → Learn → Explore → Travel → Review`

## Monorepo layout

- `apps/web` — Next.js/TypeScript client boundary.
- `services/api` — FastAPI orchestration API and domain logic.
- `docs` — source of truth (see index below).
- `.github` — issue templates for module-sized work.

## Why this repo is modular

Each domain owns its models and service logic. External providers are accessed only through interfaces in `services/api/app/providers`. A coding model should work on one module at a time and should not need global context beyond `AGENTS.md`, the relevant module, and any referenced contract.

## Docs index

| Doc | Answers |
|---|---|
| [SCOPE](docs/SCOPE.md) | What is MVP / nice-to-have / next round / non-goal; trip input variables |
| [PRODUCT](docs/PRODUCT.md) | Why, who, principles, Egypt scenario, recommendation & privacy rules |
| [ROADMAP](docs/ROADMAP.md) | Milestones M0–M8, issues, exit criteria |
| [WORKFLOW](docs/WORKFLOW.md) · [TESTING](docs/TESTING.md) | How we build: gates G0–G4, test layers, golden slices |
| [ARCHITECTURE](docs/ARCHITECTURE.md) · [MODULES](docs/MODULES.md) | Layers, pipeline, partial regeneration, module ownership |
| [DATA_MODEL](docs/DATA_MODEL.md) · [API_CONTRACTS](docs/API_CONTRACTS.md) | Entities, invariants, settlement, endpoints |
| [PROVIDERS](docs/PROVIDERS.md) · [DECISIONS](docs/DECISIONS.md) | External APIs; accepted & open decisions |
| [AI_HANDOFF](docs/AI_HANDOFF.md) | Current state and next safe task |
| [PLAN_COVERAGE](docs/PLAN_COVERAGE.md) | Plan v0.1 → repo mapping, issues found |

## MVP modules

1. Trips and preferences
2. Flight search adapters
3. Places and routing
4. Itinerary planning
5. Knowledge cards
6. Food taste matching
7. Photo spots
8. Budget, split expenses and settlement
9. During-trip daily mode

## Try it (manual testing)

`docker compose up --build`, then open http://localhost:3000 — see [docs/MANUAL_TESTING.md](docs/MANUAL_TESTING.md) for the demo trip link and a test checklist.

## Getting started (development)

Backend skeleton:

```bash
cd services/api
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
docker compose up -d postgres        # from repo root: PostGIS 16 only
alembic upgrade head                  # create schema
python scripts/seed_egypt.py          # optional: Egypt demo trip
uvicorn app.main:app --reload
```

Tests (DB tests run only when `TEST_DATABASE_URL` points at a throwaway PostGIS database; they migrate it up and back down):

```bash
ruff check . && ruff format --check .
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/trip_companion_test pytest -rs
```

CI (`.github/workflows/ci.yml`) runs lint, `alembic check`, unit + PostGIS tests, and a web typecheck on every PR.

The provider implementations in this starter are mocks. Real provider keys belong in `.env` and provider-specific adapters, never domain code.
