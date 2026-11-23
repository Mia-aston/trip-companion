# AGENTS.md — context-efficient coding rules

This repository is designed for incremental AI-assisted development.

## Before changing code

Read only:
1. this file;
2. `docs/SCOPE.md` — confirm the work is MVP for the current milestone (see `docs/ROADMAP.md`); if not, stop;
3. `docs/ARCHITECTURE.md` (layer rules);
4. the README or files inside the module you are changing;
5. directly imported shared contracts (`docs/API_CONTRACTS.md`, `docs/DATA_MODEL.md` rows you touch).

Process and gates: `docs/WORKFLOW.md`, `docs/TESTING.md`. Assumption change → `docs/DECISIONS.md` first.

Do **not** load the whole repository unless a cross-module refactor explicitly requires it.

## Module boundaries

- Domain modules must not call vendor SDKs directly.
- Vendor/API code lives under `services/api/app/providers/`.
- Itinerary logic consumes normalized domain objects, never raw provider responses.
- Recommendation logic must not infer race/ethnicity or other sensitive traits from reviewer names/photos. Taste matching is based on user-declared preferences and review content signals.
- Expense transfers are not trip expenses. Cost, payer, share and settlement are separate concepts.

## Handoff protocol

At the end of a coding task, update the closest module `README.md` or `docs/AI_HANDOFF.md` with:
- what changed;
- contracts affected;
- tests added/remaining;
- next safe task.

Keep handoff notes factual and short.
