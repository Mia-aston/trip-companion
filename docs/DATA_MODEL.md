# Data model sketch

Core entities:

- User
- TasteProfile
- Trip
- TripMember
- Booking
- FlightOption
- Place
- TripPlace
- ItineraryDay
- ItineraryItem
- KnowledgeCard
- PhotoSpot
- RestaurantRecommendation
- Expense
- ExpenseShare
- Transfer

## Expense accounting

Keep these separate:

1. **Expense** — what was purchased and total cost.
2. **Payer** — who fronted the money.
3. **ExpenseShare** — who economically owes what share.
4. **Transfer** — money one member later sent another.

Transfers never increase trip cost.
