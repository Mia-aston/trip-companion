# Trip Companion

A modular travel-planning workspace that turns dates, origin, destination, budget and preferences into an editable trip plan, then enriches it with live transport, places, food, learning cards, photo spots, practical guidance and expense settlement.

## Product loop

`Discover → Search → Plan → Learn → Explore → Travel → Review`

## Monorepo layout

- `apps/web` — Next.js/TypeScript client boundary.
- `services/api` — FastAPI orchestration API and domain logic.
- `docs` — product, architecture, provider policy, data model and handoff notes.
- `.github` — issue templates for module-sized work.

## Why this repo is modular

Each domain owns its models and service logic. External providers are accessed only through interfaces in `services/api/app/providers`. A coding model should work on one module at a time and should not need global context beyond `AGENTS.md`, the relevant module, and any referenced contract.

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

## Getting started

Backend skeleton:

```bash
cd services/api
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

The provider implementations in this starter are mocks. Real provider keys belong in `.env` and provider-specific adapters, never domain code.
