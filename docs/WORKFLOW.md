# Lean delivery workflow

Goal: docs complete before code, small modular steps, a test gate between every step. Gates are defined in `docs/TESTING.md#gates`.

## Per milestone

```text
1. Doc pass      → milestone section in ROADMAP.md is complete: MVP items, deferred items, exit test
2. Issues        → one issue per row in ROADMAP "Issues" (template: .github/ISSUE_TEMPLATE/module-task.md)   [G0]
3. For each issue:
     a. Contract PR  → Pydantic/TS models, DB migration, fixtures, tests (xfail ok)                        [G1]
     b. Impl PR      → logic until tests pass; no contract changes (if needed → back to a)                [G2]
4. Exit          → golden slice for the milestone green; AI_HANDOFF.md updated; NICE items considered     [G3]
```

Small issues may merge a+b in one PR if total diff < ~400 lines and the contract change is reviewed first in the PR description.

## Per issue (context-safe task)

A new model/session reads only: `AGENTS.md` → `docs/SCOPE.md` (tier check) → module README → contracts it touches → the issue. Not the whole repo.

Definition of Done (plan §23):
- [ ] issue has tier + acceptance criteria
- [ ] contract/schema/docs updated before or in the same PR
- [ ] no provider payload beyond the adapter
- [ ] tests for happy path **and** failure path
- [ ] AI output schema-validated + deterministic post-validator (itinerary/recommendation)
- [ ] live data has provenance/freshness
- [ ] privacy rules intact (food personalization)
- [ ] `docs/AI_HANDOFF.md` updated if state changed or a blocker appeared
- [ ] Egypt golden slices still pass if itinerary/budget touched

## Keeping it lean
- **WIP = 1 milestone.** Next milestone's docs may be drafted, not coded.
- **Tier check first.** If the issue isn't MVP for the current milestone, it waits (see SCOPE.md change rule).
- **Mocks first.** Every provider starts as mock + fixtures; live adapter is its own issue after D-02/D-03 are decided.
- **No speculative abstraction.** One live provider per capability in v1.
- **Decision log.** Changing an assumption → `docs/DECISIONS.md` entry before code continues.
- **Branches.** `m<N>/<issue-id>-slug`, PR into `main`, squash merge.
