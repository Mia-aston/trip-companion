export type TripCreate = {
  origin: string;
  destination: string;
  start_date: string;
  end_date: string;
  travellers: number;
  interests: string[];
  pace: "relaxed" | "balanced" | "packed";
};

export type Trip = TripCreate & { id: string };
