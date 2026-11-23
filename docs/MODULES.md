# Modules and contracts

| Module | Owns | Inputs | Outputs |
|---|---|---|---|
| trips | trip profile/preferences | dates, origin, destination, interests | Trip |
| flights | transport discovery | route + dates + travellers | FlightOption[] |
| places | POI lookup/details | query/location | Place[] |
| itinerary | feasibility + schedule | Trip + bookings + places | ItineraryDay[] |
| recommendations | food/photo/context ranking | user profile + place context | Recommendation[] |
| knowledge | before/during/after learning cards | place + depth | KnowledgeCard[] |
| expenses | costs/splits/transfers | Expense/Transfer events | settlement |

Cross-module communication should use typed domain objects, not database rows or raw provider JSON.
