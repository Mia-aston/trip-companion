import { FlightPicker } from "../../../../components/FlightPicker";

export default async function FlightsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <FlightPicker tripId={id} />;
}
