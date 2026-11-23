# Scope control

Purpose: keep the MVP small enough to ship and stop the project from growing sideways.
Every feature, field, endpoint and issue carries **one** tier. If it has no tier, it is not planned.

## Tiers

| Tier | Meaning | Rule |
|---|---|---|
| **MVP** | Needed for the MVP loop: create trip → plan → enrich → budget, and to pass the Egypt golden scenario. | Built in M0–M7. A milestone cannot exit with an open MVP item. |
| **NICE** | Nice-to-have. Improves MVP but the loop works without it. | Only picked up after the current milestone's exit gate passes, and only if it fits in ≤1 small PR. Otherwise → NEXT. |
| **NEXT** | Next round (post-MVP / v1.1+). Designed for (schema/contract must not block it) but not built. | Not implemented in v1. May reserve a nullable column or enum value only if a decision says so. |
| **NO** | Non-goal for v1. | Rejected. Reopening needs a decision in `DECISIONS.md`. |

### Scope-change rule
1. A new idea goes to the backlog as **NEXT** by default.
2. Promoting to MVP requires either (a) the golden scenario fails without it, or (b) it replaces an MVP item of similar size. Record it in `DECISIONS.md`.
3. One milestone in progress at a time. NICE items never block a milestone exit.

## MVP loop (v1)

`Create trip + preferences → select flight (external booking link) → discover places → generate itinerary → lock / edit / partially regenerate → place cards (Know / Eat / Photo / Practical) → expenses, splits, transfers, settlement`.

## Trip input variables

These are the inputs the planner and budget engine may use. Anything not listed is out of scope until added here.

### Travellers
| Variable | Type / values | Default | Tier | Used by |
|---|---|---|---|---|
| `adults` | int 1–20 | 1 | MVP | flights (pax), budget estimate, splits |
| `children` | list of ages 2–17 | [] | MVP | flights (pax type), activity filtering, pace |
| `infants` | int 0–adults (age <2) | 0 | NICE | flights (lap infant fare) |
| `travellers` (derived) | adults + len(children) + infants | — | MVP | replaces the current single `travellers` field |
| `members` | named trip members (people who pay/owe) | creator | MVP | expenses, settlement (members ≠ travellers: a parent can pay for kids) |
| `member.role` | owner / editor / viewer | owner | MVP (owner only) / NEXT (editor, viewer + sharing) | permissions |
| `mobility_needs` | none / limited_walking / wheelchair / stroller | none | MVP | max walking, place accessibility, day capacity |

### Where & when
| Variable | Type / values | Default | Tier | Used by |
|---|---|---|---|---|
| `origin` | city / IATA | — | MVP | flights |
| `destinations` | ordered list of stops `{place, nights}` (multi-city) | 1 stop | MVP | itinerary days, routing (Egypt is multi-city) |
| `start_date`, `end_date` | dates | — | MVP | everything |
| `flexible_dates` | ± N days / month only | none | NEXT | destination inspiration |
| `open_destination` | "anywhere warm in Nov" | — | NEXT | destination inspiration |
| `arrival_at`, `departure_at` | datetimes (from selected flight or manual) | — | MVP | first/last-day capacity |
| `timezone` per stop | IANA tz | from place | MVP | all time math |
| `accommodation` | per stop: booked hotel or `area` | none | MVP (manual entry) / NEXT (hotel search) | day start/end point, routing |

### Budget
| Variable | Type / values | Default | Tier | Used by |
|---|---|---|---|---|
| `base_currency` | ISO-4217 | user default | MVP | trip cost view |
| `settlement_currency` | ISO-4217 | = base_currency | MVP | settlement |
| `budget_total` | money, optional | none | MVP | warnings, ranking (price level) |
| `budget_scope` | per_trip / per_person | per_trip | MVP | estimate |
| `budget_split` | per category (flights, stay, food, activities, transport) | none | NICE | budget view |
| `price_level` | 1–4 | 2 | MVP | place/food ranking |

### Preferences & constraints
| Variable | Type / values | Default | Tier | Used by |
|---|---|---|---|---|
| `pace` | relaxed / balanced / packed | balanced | MVP | day capacity (stops/day, buffer) |
| `day_window` | earliest start, latest end (e.g. 08:00–21:00) | 09:00–20:00 | MVP | day capacity |
| `interests` | tags from a fixed list (history, food, photo, nature, nightlife, shopping, art, adventure) | [] | MVP | candidate scoring |
| `must_do` | places/activities that must be scheduled | [] | MVP | hard constraint, locked |
| `avoid` | places/categories to exclude | [] | MVP | hard filter |
| `dietary` | vegetarian, vegan, halal, kosher, gluten_free, nut_allergy, … | [] | MVP | **hard** filter for food; allergy → "verify with venue" warning |
| `taste_profile` | declared taste vector (see Food) | neutral | MVP (declared) / NEXT (learned from feedback) | food ranking |
| `flight_prefs` | max_stops, cabin, bags, self_transfer_ok, time-of-day | any/economy/1 bag/no | MVP (max_stops, cabin, bags) / NICE (time-of-day, self-transfer) | flight filter |
| `weather_sensitive` | flag on activities (e.g. balloon) | false | MVP (flag + manual fallback) / NICE (live weather) | regeneration trigger |
| `language` | UI / content language | en | MVP (en, vi) | knowledge cards |

## Scope per module

| Module | MVP | NICE | NEXT | NO (v1) |
|---|---|---|---|---|
| Trip core | create/edit/delete trip, travellers, members, destinations, preferences, constraints, manual bookings, plan versions | trip duplication/templates | collaborative real-time editing, sharing roles | social feed |
| Flights | mock + 1 live adapter, normalized offers, filters (price/stops/bags), select → hard constraint, external booking link, fetched_at + expiry | time-of-day filter, self-transfer flag | price alerts, flexible-date inspiration | direct ticketing, refunds |
| Places | search/details via 1 adapter, normalized place (hours, rating, price level, accessibility) | photos metadata | multiple providers merged | scraping protected sites |
| Routing | route matrix via 1 adapter, travel-time penalties, infeasibility | transit-mode choice | live traffic replan | — |
| Itinerary | generate, edit, lock, partial regenerate (day scope), validator, plan versions + diff, "why this plan" | drag-and-drop reorder UI | multi-day scope regenerate with re-flowing, auto-optimise order | — |
| Knowledge | before/at-place/after cards grounded in places, sources + generated_at, reading state | — | audio guide | visa legal advice |
| Food | declared TasteProfile, dietary hard filter, rank + "match %" explanation, review signal extraction (non-sensitive) | — | learned taste from feedback | race/ethnicity inference |
| Photo spots | curated spots schema + read API, provenance | — | user submissions (needs moderation, D-05), community spots | — |
| Budget | multi-currency expenses, payer, splits (equal/exact/percent), transfers, settlement, FX snapshot | category budget view, CSV export | receipt OCR, bank connectors | full accounting |
| During-trip | Today view, skip / running late / replan rest of today | nearby fallback suggestions | offline packs, push notifications | — |
| Post-trip | — (actual vs estimate lives in Budget) | visited/skipped marking, learning recap | trip summary, journal, preference learning | — |
| Platform | email/OAuth auth abstraction (D-01), delete-my-data, mock providers locally, CI | — | mobile app | microservices |
