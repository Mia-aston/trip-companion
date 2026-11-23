# Product definition

Source: plan v0.1 §1–7, §9 (`docs/archive/`). Scope tiers live in `docs/SCOPE.md`.

## Core promise

An AI-assisted travel **workspace**, not just an itinerary generator. It keeps the trip as an evolving plan and surfaces the right planning, knowledge and recommendations at the right moment: before, during and after the trip.

**Thesis:** the value is not "AI writes a schedule" but that the app understands trip context over time — and when the user changes one part (drop Aswan, stay in Luxor), only the affected block is regenerated.

## Principles

| Principle | Meaning |
|---|---|
| Plan from constraints, not vibes | Arrival/departure, opening hours, travel time, energy, luggage, bookings, must-dos limit the plan before any LLM prose. |
| LLM is planner, not database | Flights, places, hours, routes, prices come from providers. The LLM ranks, composes, explains, regenerates. |
| Partial regeneration by default | Changing a day/stop never breaks bookings or locked days. |
| Explain why | Every day / restaurant / route recommendation shows why it was chosen. |
| Multi-currency native | Original currency is canonical; conversions are derived; transfers are not trip cost. |
| Preference > demographic proxy | Food matching uses the declared taste profile + review content, never inferred race/ethnicity. |
| Modular by contract | Provider, domain, orchestration and UI talk through typed contracts; each module builds/tests alone. |
| Trust through provenance | Every user-visible fact is labelled: live provider data (with `fetched_at`), user input, or AI inference. |

## Users & jobs-to-be-done

Primary user: an independent traveller or small group (2–6) planning on their own, with clear preferences (budget, food, history, photography, pace, comfort, must-dos), who will change plans mid-trip.

1. "I have dates and a budget — help me find a reasonable flight." *(MVP: known destination. Destination inspiration = NEXT.)*
2. "I picked a destination — give me a feasible schedule around my flights and bookings." *(MVP)*
3. "At a site — briefly explain what I'm looking at and what to notice." *(MVP)*
4. "Hungry — suggest places that fit my taste and my next stop, not just top-rated." *(MVP)*
5. "Plans changed — fix only the affected block, don't reset the trip." *(MVP)*
6. "Travelling together — track who paid, who owes, reimbursements, final settlement." *(MVP)*

## Golden scenario: Egypt

The architecture acceptance test. Full fixture spec: `docs/TESTING.md#golden-scenario-egypt`.

Late arrival in Cairo → Cairo/Giza → overnight desert → Luxor → weather-sensitive balloon → user removes the Aswan day trip and turns 6 Nov into Luxor downtown. The system must keep hotel and flight bookings, replace only 6 Nov, update budget/prep, and produce no conflicts. Two members (Mia, QA) pay in USD/EUR/GBP/EGP and settle without double-counting transfers.

> If the engine has to regenerate the whole trip or loses booking constraints here, the architecture is not done.

## Experience

### Before (MVP unless marked)
1. Create trip (variables in `SCOPE.md`)
2. Search / select flight → becomes hard time constraint
3. Set accommodation or area per stop (manual)
4. Generate itinerary
5. Review travel-time and opening-hours conflicts
6. Lock bookings / must-do items
7. Prep checklist *(NICE)*
8. Learn-before-you-go pack (knowledge cards)
9. Seed budget

### During
"Today" view. Each stop shows time, route, booking state and up to 5 actions: **Know, Navigate, Eat, Photo, Practical**. Actions: skip, running late, replan rest of today. Nearby fallback = NICE.

```text
TODAY — Luxor
07:00 Breakfast
09:00 Luxor Museum      [Know] [Photo] [Eat nearby]
12:30 Downtown lunch    [Taste match 89%]
15:00 Corniche / café
20:30 Collect bags
22:30 Airport
```

### After
Reconcile actual expenses (MVP, in Budget). Visited vs skipped, learning recap (NICE). Journal, saved spots, preference learning (NEXT).

## Recommendation systems

### Food taste engine
- `TasteProfile` = user-declared taste + (NEXT) learned feedback.
- Review text is used **only** to extract content signals:

| Signal group | Examples |
|---|---|
| Taste | spicy, savory, sour, sweet, bitter, rich, smoky |
| Texture | crispy, chewy, creamy, broth-heavy |
| Cuisine familiarity | reviewer *states* "I eat Sichuan food regularly" |
| Authenticity | local-style, tourist-adjusted, traditional preparation |
| Context | distance to next stop, open now, price, reservation need, dietary fit |
| Confidence | review volume, recency, consistency across sources |

```text
taste_match = w1*preference_similarity + w2*cuisine_fit + w3*context_fit
            + w4*quality_confidence - w5*travel_penalty      (0..1, shown as %)
```
Dietary restrictions are a hard filter applied before scoring. UI says "Match for your taste: 88%". Review language may be a transparent display filter, never a reviewer identity.

### Knowledge cards
| Moment | Card types |
|---|---|
| Before | context primer, timeline, key concepts, names to know |
| At place | what to look for, 3–5 min explanation, practical cue |
| After *(NICE)* | compare places visited, recap, deeper reading |

Every card stores `sources[]` and `generated_at`.

### Photo spots
Sub-place data, not generic place photos: label, coordinate or relative description, best time/light, shot direction, crowd note, lens/phone hint, accessibility, provenance, confidence. MVP = curated only (D-05).

## Safety, privacy & responsible recommendation

- Never infer race, ethnicity, religion, health, sexual orientation or other sensitive traits from reviewer/user content to rank anything.
- No nationality/race proxy where a taste vector can express the preference directly.
- Declared dietary restrictions are hard constraints; high-stakes allergies show "verify directly with the venue".
- Visa/immigration info shows source + freshness and never asserts eligibility.
- Prices, opening hours and availability carry a timestamp and a refresh path.
- Don't keep raw review/profile data longer than needed; store extracted non-sensitive signals where permitted.
- Users can delete trips, preferences and their own contributions (MVP: delete trip + delete account data).
