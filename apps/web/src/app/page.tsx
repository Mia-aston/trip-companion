import { CreateTripForm } from "../components/CreateTripForm";

export default function HomePage() {
  return (
    <>
      <h1>Plan a trip</h1>
      <p className="muted">Dates, stops and preferences first — the itinerary is built from these constraints later.</p>
      <CreateTripForm />
    </>
  );
}
