import { ItineraryEditor } from "../../../../components/ItineraryEditor";

export default async function ItineraryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ItineraryEditor tripId={id} />;
}
