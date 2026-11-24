"use client";

import { useEffect, useState, type FormEvent } from "react";

import { ApiRequestError, getTrip, searchFlights, selectOffer } from "../lib/api";
import { money, shortDate } from "../lib/format";
import { label } from "../lib/options";
import type { Booking, FlightOffer, FlightSearchResult, SelectResult, Trip, TripFlightSearch } from "../types";

type Direction = TripFlightSearch["direction"];

function clock(iso: string, timeZone: string): string {
  return new Intl.DateTimeFormat("en-GB", { timeZone, hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(new Date(iso));
}

function localDay(iso: string, timeZone: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone }).format(new Date(iso));
}

function duration(minutes: number): string {
  return `${Math.floor(minutes / 60)}h ${String(minutes % 60).padStart(2, "0")}m`;
}

function minutesLeft(iso: string, now: number): number {
  return Math.max(0, Math.floor((Date.parse(iso) - now) / 60000));
}

function OfferRow({ offer, busy, now, onSelect }: { offer: FlightOffer; busy: boolean; now: number; onSelect: (o: FlightOffer) => void }) {
  const first = offer.segments[0];
  const last = offer.segments[offer.segments.length - 1];
  const nextDay = localDay(offer.arrives_at, last.destination_timezone) > localDay(offer.departs_at, first.origin_timezone);
  const left = minutesLeft(offer.expires_at, now);
  return (
    <li className="offer" data-testid="offer">
      <div className="offer-main">
        <strong className="offer-times">
          {clock(offer.departs_at, first.origin_timezone)} {first.origin} → {clock(offer.arrives_at, last.destination_timezone)}
          {nextDay && <sup> +1</sup>} {last.destination}
        </strong>
        <span className="muted">
          {offer.stops === 0 ? "Direct" : `${offer.stops} stop${offer.stops > 1 ? "s" : ""} via ${offer.segments.slice(1).map((s) => s.origin).join(", ")}`} ·{" "}
          {duration(offer.duration_minutes)} · {first.carrier_name} {offer.segments.map((s) => s.flight_number).join(" + ")}
        </span>
        <span className="muted">
          {label(offer.cabin)} · {offer.baggage.checked_bags} checked bag{offer.baggage.checked_bags === 1 ? "" : "s"}
          {offer.refundable && " · refundable"} · <span data-testid="expiry">{left > 0 ? `price held ~${left} min` : "expired"}</span>
        </span>
      </div>
      <div className="offer-side">
        <strong className="price">{money(offer.total)}</strong>
        <button className="primary" type="button" disabled={busy || left === 0} onClick={() => onSelect(offer)} aria-label={`Select ${offer.segments.map((s) => s.flight_number).join(" ")}`}>
          Select
        </button>
        {offer.booking_url && (
          <a href={offer.booking_url} target="_blank" rel="noopener noreferrer" className="muted">
            Book on provider ↗
          </a>
        )}
      </div>
    </li>
  );
}

function current(trip: Trip, direction: Direction): Booking | undefined {
  const flights = trip.bookings.filter((b) => b.kind === "flight" && b.status !== "cancelled").sort((a, b) => a.starts_at.localeCompare(b.starts_at));
  if (!flights.length) return undefined;
  return direction === "outbound" ? flights[0] : flights.length > 1 ? flights[flights.length - 1] : undefined;
}

function DirectionPanel({ trip, direction, onSelected }: { trip: Trip; direction: Direction; onSelected: (r: SelectResult) => void }) {
  const outbound = direction === "outbound";
  const [from, setFrom] = useState(outbound ? trip.origin.slice(0, 3).toUpperCase() : "");
  const [to, setTo] = useState(outbound ? "" : trip.origin.slice(0, 3).toUpperCase());
  const [date, setDate] = useState(outbound ? trip.start_date : trip.end_date);
  const [stops, setStops] = useState("");
  const [bags, setBags] = useState("");
  const [sort, setSort] = useState<"price" | "duration">("price");
  const [result, setResult] = useState<FlightSearchResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ message: string; details: string[] } | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const booked = current(trip, direction);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(t);
  }, []);

  function fail(err: unknown) {
    setError(err instanceof ApiRequestError ? { message: err.message, details: err.details } : { message: "Could not reach the API.", details: [] });
  }

  async function search(e?: FormEvent) {
    e?.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setResult(
        await searchFlights(trip.id, {
          direction,
          from_airport: from.toUpperCase(),
          to_airport: to.toUpperCase(),
          date,
          max_stops: stops === "" ? null : Number(stops),
          checked_bags: bags === "" ? null : Number(bags),
          cabin: null,
          sort,
        }),
      );
      setNow(Date.now());
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function choose(offer: FlightOffer) {
    setBusy(true);
    setError(null);
    try {
      onSelected(await selectOffer(trip.id, offer.id));
      setResult(null);
    } catch (err) {
      if (err instanceof ApiRequestError && err.status === 409) setResult(null); // stale prices: force a fresh search
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card" aria-label={outbound ? "Outbound flight" : "Return flight"}>
      <h2>{outbound ? "Outbound" : "Return"}</h2>
      <p className="muted" data-testid={`current-${direction}`}>
        {booked ? `Current: ${booked.title} (${booked.status})` : "No flight booked yet."}
      </p>
      <form onSubmit={search} aria-label={`Search ${direction} flights`}>
        <div className="grid">
          <label>
            From (IATA)
            <input required pattern="[A-Za-z]{3}" maxLength={3} value={from} onChange={(e) => setFrom(e.target.value)} />
          </label>
          <label>
            To (IATA)
            <input required pattern="[A-Za-z]{3}" maxLength={3} value={to} onChange={(e) => setTo(e.target.value)} />
          </label>
          <label>
            Date
            <input type="date" required value={date} onChange={(e) => setDate(e.target.value)} />
          </label>
          <label>
            Stops
            <select value={stops} onChange={(e) => setStops(e.target.value)}>
              <option value="">Trip preference</option>
              <option value="0">Direct only</option>
              <option value="1">Up to 1</option>
              <option value="2">Up to 2</option>
            </select>
          </label>
          <label>
            Checked bags
            <select value={bags} onChange={(e) => setBags(e.target.value)}>
              <option value="">Trip preference</option>
              <option value="0">Not needed</option>
              <option value="1">At least 1</option>
              <option value="2">At least 2</option>
            </select>
          </label>
          <label>
            Sort
            <select value={sort} onChange={(e) => setSort(e.target.value as "price" | "duration")}>
              <option value="price">Cheapest</option>
              <option value="duration">Fastest</option>
            </select>
          </label>
        </div>
        <div className="actions">
          <button className="primary" type="submit" disabled={busy}>
            Search {outbound ? "outbound" : "return"}
          </button>
        </div>
      </form>

      {error && (
        <div className="error" role="alert">
          <strong>{error.message}</strong>
          {error.details.length > 0 && <ul>{error.details.map((d) => <li key={d}>{d}</li>)}</ul>}
        </div>
      )}

      {result && (
        <>
          <p className="muted" data-testid={`summary-${direction}`}>
            {result.offers.length} option{result.offers.length === 1 ? "" : "s"} for {result.search.adults + result.search.children_ages.length + result.search.infants} passenger
            {result.search.adults + result.search.children_ages.length + result.search.infants === 1 ? "" : "s"} on {shortDate(result.search.date)}
            {result.filtered_out > 0 && ` · ${result.filtered_out} hidden by your filters`}
          </p>
          {result.offers.length > 0 ? (
            <ul className="offers">
              {result.offers.map((o) => (
                <OfferRow key={o.id} offer={o} busy={busy} now={now} onSelect={choose} />
              ))}
            </ul>
          ) : (
            <p className="muted">No flights match. Try allowing more stops or fewer bags.</p>
          )}
        </>
      )}
    </section>
  );
}

export function FlightPicker({ tripId }: { tripId: string }) {
  const [trip, setTrip] = useState<Trip | null>(null);
  const [selected, setSelected] = useState<SelectResult | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    getTrip(tripId).then(setTrip).catch((err) => setProblem(err instanceof ApiRequestError && err.status === 404 ? "Trip not found." : err.message));
  }, [tripId]);

  async function onSelected(r: SelectResult) {
    setSelected(r);
    setTrip(await getTrip(tripId));
  }

  if (!trip) return problem ? <div className="error" role="alert">{problem}</div> : <p className="muted">Loading…</p>;

  return (
    <article>
      <p>
        <a href={`/trips/${trip.id}`}>← {trip.title}</a>
      </p>
      <h1>Flights</h1>
      <p className="muted">Prices are held for a short time. Selecting adds a tentative booking; you book on the provider's site.</p>

      {selected && (
        <div className="card notice" role="status" data-testid="selected">
          <strong>Added: {selected.booking.title}</strong> — {money(selected.booking.cost!)} · tentative
          {selected.affected_dates.length > 0 ? (
            <p>
              Free time changed on {selected.affected_dates.map(shortDate).join(", ")}.{" "}
              <a href={`/trips/${trip.id}/itinerary`}>Re-plan in the itinerary →</a>
            </p>
          ) : (
            <p className="muted">No change to your free time.</p>
          )}
        </div>
      )}

      <DirectionPanel trip={trip} direction="outbound" onSelected={onSelected} />
      <DirectionPanel trip={trip} direction="return" onSelected={onSelected} />
    </article>
  );
}
