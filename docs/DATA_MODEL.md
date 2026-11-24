# Data model

Source: plan v0.1 §11, §14. Input variables and their tiers: `docs/SCOPE.md#trip-input-variables`.
Status column: **built** = in a migration (`0001`–`0005`); **change** = exists but must be updated (CORE-001/002); **todo** = not yet built.

## Entities

| Entity | Purpose | Key fields | Tier | Milestone | Status |
|---|---|---|---|---|---|
| `users` | account/profile; no inferred sensitive traits | id, email, display_name, default_currency, locale | MVP | M1 | built (0002) |
| `taste_profiles` | declared taste (+ learned, NEXT) | user_id, vector (taste/texture), cuisines_liked[], dietary[], updated_at | MVP | M5 | todo |
| `trips` | the trip | id, owner_id, title, status (draft/planned/active/done), start/end_date, adults, children_ages[], infants, origin, base_currency, settlement_currency, budget_total, budget_scope, pace, day_start, day_end, interests[], dietary[], mobility_needs, price_level, flight_prefs JSON | MVP | M1 | built (0002) |
| `trip_stops` | ordered destinations (multi-city) | trip_id, seq, place_id/city, nights, arrive_on, leave_on, timezone, accommodation_booking_id / area | MVP | M1 | built (0002) |
| `trip_members` | people who pay/owe | trip_id, user_id?, display_name, role, currency_pref | MVP | M1 | built (0002) |
| `trip_constraints` | hard/soft constraints | trip_id, kind (must_do/avoid/time_window — dietary & mobility are trip fields, A-09), hardness (hard/soft), payload JSON (typed per kind), source (user/booking/system), locked | MVP | M1 | built (0002) |
| `transport_options` | normalized flight offer snapshot from a search | trip_id, search_id, direction, provider, offer_id, offer JSON (normalized `FlightOffer`), total_amount, currency, stops, departs_at, arrives_at, fetched_at, expires_at, selected_at | MVP | M4 | built (0005) |
| `bookings` | confirmed external booking (manual in MVP) | trip_id, kind (flight/hotel/activity/transport), title, starts_at, ends_at, place_id?, reference, cost → expense_id?, status | MVP | M1 | built (0002) |
| `places` | canonical normalized place | provider, provider_place_id, name, location (geography), categories[], opening_hours JSON (weekly periods), rating, rating_count, price_level, wheelchair_accessible, timezone, typical_visit_minutes, fetched_at | MVP | M2 | built (0003) |
| `trip_places` | place state within a trip | trip_id, place_id, state (candidate/saved/scheduled/visited/skipped), score | MVP | M2 | todo |
| `plan_versions` | immutable plan snapshots | trip_id, version (unique per trip), parent_version, created_by (planner/user/system), reason, explanation, diff JSON (vs parent), warnings JSON, created_at | MVP | M3 | built (0004) |
| `itinerary_days` | a day in a plan version | plan_version_id, date, stop_seq, capacity_minutes, notes[] | MVP | M3 | built (0004) |
| `itinerary_items` | scheduled block | day_id, item_key (stable across versions), position, starts_at, ends_at, kind (place/booking/transfer/meal/custom/free), title, place_id?, booking_id?, locked, weather_sensitive, source (planner/user/booking), why | MVP | M3 | built (0004) |
| `route_legs` | cached travel times | provider, mode, origin_id, destination_id (domain place ids), duration_s, distance_m, fetched_at | MVP | M2 | built (0003) |
| `knowledge_cards` | before/at/after content | place_id, moment, language, body, sources JSON, generated_at, model | MVP | M5 | todo |
| `card_reads` | reading state | user_id, card_id, read_at | MVP | M5 | todo |
| `photo_spots` | sub-place shot data | place_id, label, location?, relative_desc, best_time, direction, crowd_note, lens_hint, accessibility, provenance, confidence | MVP (curated) | M5 | todo |
| `restaurant_signals` | extracted non-sensitive review signals | place_id, signal vector, cuisine tags, authenticity, confidence, source_count, extracted_at | MVP | M5 | todo |
| `expenses` | what was bought | trip_id, description, category, original_amount, original_currency, payer_member_id, incurred_on, idempotency_key | MVP | M6 | **change** (rename amount→original_amount, add category, idempotency_key) |
| `expense_splits` | who owes what | expense_id, member_id, rule (equal/exact/percent), value, amount_original | MVP | M6 | **change** (table is `expense_shares`; add rule/value) |
| `transfers` | member→member money | trip_id, sender, recipient, original_amount, original_currency, sent_on, idempotency_key | MVP | M6 | built (rename amount→original_amount) |
| `fx_rates` | timestamped FX snapshots | base, quote, rate, as_of, provider | MVP | M6 | todo |
| `provider_snapshots` | short-lived fetch metadata | provider, kind, request_hash, request JSON, result_ids[], fetched_at, expires_at (no raw payloads) | MVP | M2 | built (0003) |
| `prep_tasks` | prep checklist | trip_id, title, due_on, done | NICE | M7 | — |

Not in v1 (NEXT): collaborative edit sessions, user-submitted photo spots, receipts, bank connections, learned taste history.

## Expense invariants

1. `original_amount` + `original_currency` are canonical input and never overwritten.
2. Converted values are derived from a timestamped `fx_rates` row; a finalized expense may freeze its rate (D-06).
3. Payer ≠ share owner. A payer may have zero share.
4. Splits of an expense sum exactly to the expense (property-tested; rounding remainder goes to the payer).
5. Transfers/reimbursements are **not** trip cost; they only affect settlement.
6. Settlement is recomputable from expenses + splits + transfers at any time; it is never stored as truth.

## Settlement

All values normalized to `settlement_currency`:
```text
member_net = paid_for_trip - cost_share + transfers_sent - transfers_received
  > 0  → member should receive
  < 0  → member should pay
Σ member_net = 0   (property-tested)
```
> Sign note: the plan v0.1 formula (`+ transfers_received - transfers_sent`) has the transfer signs reversed — sending a reimbursement *reduces* what you owe, so it must be added. Fixed here; see A-05.

UI shows side by side: total trip cost · cost share per person · paid directly · transfers · remaining settlement. Transfers never appear in total trip cost.

### Egypt expense case (M6 exit gate)
| Object | Detail |
|---|---|
| Expense | The View Hotel €128.62; payer QA; split 50/50 |
| Expense | Balloon $150; payer QA; split 50/50 |
| Expense | Railway £101.56; payer Mia; split 50/50 |
| Transfer | QA → Mia £50.28 (reimbursement) |
| Transfer | Mia → QA £x (repayment) |
