# AI handoff log

## Current baseline

The repository contains product/architecture decisions plus a minimal FastAPI domain skeleton.

### Implemented
- typed Trip request/response model;
- provider protocol for flights/places;
- mock flight provider;
- deterministic itinerary skeleton;
- taste-profile matching primitives;
- expense/share/transfer settlement primitives.

### Next safe tasks
1. Add SQLAlchemy models + migrations for Trip and Expense domains.
2. Add flight provider contract tests.
3. Add place normalization model and mock provider fixtures.
4. Build `/trips/{id}/itinerary` around persisted data.
5. Add Next.js create-trip form against the API.

### Context rule
Pick one task, read only its module + shared contract. Do not redesign unrelated modules.
