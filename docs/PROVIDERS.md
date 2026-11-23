# Provider strategy

## Flights

Use an adapter interface. Candidate production providers may include Skyscanner or Duffel. Keep a mock adapter for deterministic development/tests.

## Places

Use a normalized Place model so Google Places, Foursquare or another provider can be swapped. Respect provider content/display/storage policies.

## Reviews and food matching

Do not infer reviewer race/ethnicity from names, photos, language or other proxies. Extract food-relevant content signals only, e.g.:
- spice;
- sweetness;
- saltiness;
- richness;
- texture;
- authenticity claims;
- value;
- cuisine familiarity explicitly stated in review text;
- review language as language, not ethnicity.

## Maps/routing

Keep routing behind a provider boundary. The itinerary engine should consume travel-time matrices or normalized routes.
