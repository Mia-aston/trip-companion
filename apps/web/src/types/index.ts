// Contract types are generated from the API's OpenAPI document (A-08).
// Do not hand-edit api.gen.ts: run `python scripts/export_openapi.py` in services/api, then `npm run gen:types`.
import type { components } from "./api.gen";

type Schemas = components["schemas"];

export type Money = Schemas["Money"];
export type TimeWindow = Schemas["TimeWindow"];
export type Pace = Schemas["Pace"];
export type Interest = Schemas["Interest"];
export type DietaryRestriction = Schemas["DietaryRestriction"];
export type MobilityNeeds = Schemas["MobilityNeeds"];

export type TripCreate = Schemas["TripCreate"];
export type TripUpdate = Schemas["TripUpdate"];
export type Trip = Schemas["Trip"];
export type Stop = Schemas["Stop"];
export type Member = Schemas["Member"];
export type MemberCreate = Schemas["MemberCreate"];
export type ConstraintCreate = Schemas["MustDoCreate"] | Schemas["AvoidCreate"] | Schemas["TimeWindowConstraintCreate"];
export type Constraint = Schemas["MustDo"] | Schemas["Avoid"] | Schemas["TimeWindowConstraint"];
export type Booking = Schemas["Booking"];
export type BookingCreate = Schemas["BookingCreate"];
export type ApiError = Schemas["ErrorResponse"];
