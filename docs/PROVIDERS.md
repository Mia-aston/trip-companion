# Provider strategy

Source: plan v0.1 §8, §15, §24. Provider facts were checked against official docs on 23 Nov 2026 (links below).
Domain code never calls a vendor SDK or sees a vendor payload. Every capability = protocol + mock + (later) one live adapter, all passing the same contract suite.

| Capability | Candidate provider | Design note | Tier | Decision |
|---|---|---|---|---|
| Flights | Skyscanner Flights Live Prices (create/poll); Duffel Offers | Search adapter; offers expire → store `expires_at`, never persist a stale offer as guaranteed fare; refresh before select | MVP | D-03 |
| Places | Google Places API (New): Text/Nearby Search, Details, Photos | Normalize IDs, location, categories, hours, rating, price level; respect attribution, storage and EEA terms | MVP | D-02 |
| Routing | Google Routes API: Compute Routes, Route Matrix | Itinerary consumes a normalized RouteMatrix; map presentation isolated | MVP | D-02 |
| FX | adapter (TBD) | timestamped rates; frozen rate for finalized expenses | MVP | D-06 |
| LLM | adapter (TBD) | structured outputs only; planner/explainer/extractor behind interfaces | MVP | D-07 |
| Weather | adapter (TBD) | only for weather-sensitive activities | NICE | — |
| Knowledge | curated sources + web retrieval + LLM | store source refs + `generated_at` | MVP | — |
| User-generated | first-party ratings, taste feedback, photo-spot feedback | strongest personalization layer over time | NEXT | D-05 |

## Rules
- **Freshness:** every volatile snapshot has `fetched_at` + TTL; UI shows staleness.
- **Fallback:** provider failure → degraded response with stale label, never fabricated data.
- **Fixtures:** recorded responses are sanitized (no keys, no personal data) and stored in `tests/fixtures/<provider>/`.
- **Rate limits:** one central client per provider with retry/backoff; quotas in M8.
- **Keys:** only in `.env` / secret store, read by adapters; never in domain or web.

## Reviews and food matching
Do not infer reviewer race/ethnicity from names, photos, language or other proxies. Extract food-relevant content signals only: taste (spicy, savory, sour, sweet, bitter, rich, smoky), texture, authenticity claims, value, cuisine familiarity explicitly stated in the text, review language as language only.

## References
- Skyscanner Flights Live Prices — https://developers.skyscanner.net/docs/flights-live-prices/overview
- Google Places API (New) — https://developers.google.com/maps/documentation/places/web-service/quick-reference
- Google Routes API — https://developers.google.com/maps/documentation/routes/quick-reference
- Duffel Offers — https://duffel.com/docs/api/offers
- OpenAI Structured Outputs — https://developers.openai.com/api/docs/guides/structured-outputs
