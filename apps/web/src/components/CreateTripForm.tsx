"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";

import { ApiRequestError, createTrip } from "../lib/api";
import { DIETARY, INTERESTS, MOBILITY, PACES, label, nightsBetween } from "../lib/options";
import type { DietaryRestriction, Interest, MobilityNeeds, Pace, TripCreate } from "../types";

type StopDraft = { city: string; nights: number };

function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

export function CreateTripForm() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [origin, setOrigin] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [adults, setAdults] = useState(1);
  const [childrenAges, setChildrenAges] = useState("");
  const [infants, setInfants] = useState(0);
  const [stops, setStops] = useState<StopDraft[]>([{ city: "", nights: 0 }]);
  const [baseCurrency, setBaseCurrency] = useState("GBP");
  const [budget, setBudget] = useState("");
  const [pace, setPace] = useState<Pace>("balanced");
  const [interests, setInterests] = useState<Interest[]>([]);
  const [dietary, setDietary] = useState<DietaryRestriction[]>([]);
  const [mobility, setMobility] = useState<MobilityNeeds>("none");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<{ message: string; details: string[] } | null>(null);

  const tripNights = nightsBetween(startDate, endDate);
  const stopNights = stops.reduce((sum, s) => sum + (Number.isFinite(s.nights) ? s.nights : 0), 0);
  const nightsOk = tripNights !== null && tripNights >= 0 && stopNights === tripNights;

  const ages = useMemo(
    () =>
      childrenAges
        .split(",")
        .map((a) => a.trim())
        .filter(Boolean)
        .map(Number),
    [childrenAges],
  );

  function updateStop(index: number, patch: Partial<StopDraft>) {
    setStops((current) => current.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    const payload: TripCreate = {
      title,
      origin,
      start_date: startDate,
      end_date: endDate,
      adults,
      children_ages: ages,
      infants,
      stops: stops.map((s) => ({ city: s.city, nights: s.nights })),
      base_currency: baseCurrency.toUpperCase(),
      budget: budget ? { total: { amount: Number(budget).toFixed(2), currency: baseCurrency.toUpperCase() } } : null,
      pace,
      interests,
      dietary,
      mobility_needs: mobility,
    };
    try {
      const trip = await createTrip(payload);
      router.push(`/trips/${trip.id}`);
    } catch (err) {
      if (err instanceof ApiRequestError) setError({ message: err.message, details: err.details });
      else setError({ message: "Could not reach the API. Is it running?", details: [] });
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} aria-label="Create trip">
      <section className="card">
        <h2>Trip</h2>
        <div className="grid">
          <label>
            Title
            <input name="title" required maxLength={120} value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label>
            From
            <input name="origin" required minLength={1} placeholder="LON" value={origin} onChange={(e) => setOrigin(e.target.value)} />
          </label>
          <label>
            Start date
            <input name="start_date" type="date" required value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </label>
          <label>
            End date
            <input name="end_date" type="date" required value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </label>
        </div>
      </section>

      <section className="card">
        <h2>Stops</h2>
        {stops.map((stop, i) => (
          <div className="row" key={i} style={{ marginBottom: 8 }}>
            <label>
              City {i + 1}
              <input
                name={`stop-${i}-city`}
                required
                value={stop.city}
                onChange={(e) => updateStop(i, { city: e.target.value })}
              />
            </label>
            <label style={{ flex: "0 1 110px" }}>
              Nights
              <input
                name={`stop-${i}-nights`}
                type="number"
                min={0}
                max={60}
                required
                value={stop.nights}
                onChange={(e) => updateStop(i, { nights: e.target.valueAsNumber })}
              />
            </label>
            {stops.length > 1 && (
              <button type="button" onClick={() => setStops((s) => s.filter((_, j) => j !== i))} aria-label={`Remove stop ${i + 1}`}>
                Remove
              </button>
            )}
          </div>
        ))}
        <div className="row">
          <button type="button" onClick={() => setStops((s) => [...s, { city: "", nights: 0 }])}>
            Add stop
          </button>
          {tripNights !== null && (
            <span className={`hint ${nightsOk ? "good" : "bad"}`} data-testid="nights-hint">
              {stopNights} of {tripNights} nights allocated
            </span>
          )}
        </div>
      </section>

      <section className="card">
        <h2>Travellers</h2>
        <div className="grid">
          <label>
            Adults
            <input name="adults" type="number" min={1} max={20} value={adults} onChange={(e) => setAdults(e.target.valueAsNumber)} />
          </label>
          <label>
            Children ages (comma-separated)
            <input name="children_ages" placeholder="e.g. 6, 9" value={childrenAges} onChange={(e) => setChildrenAges(e.target.value)} />
          </label>
          <label>
            Infants (under 2)
            <input name="infants" type="number" min={0} max={20} value={infants} onChange={(e) => setInfants(e.target.valueAsNumber)} />
          </label>
          <label>
            Mobility
            <select name="mobility_needs" value={mobility} onChange={(e) => setMobility(e.target.value as MobilityNeeds)}>
              {MOBILITY.map((m) => (
                <option key={m} value={m}>
                  {label(m)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <section className="card">
        <h2>Budget & preferences</h2>
        <div className="grid">
          <label>
            Currency
            <input name="base_currency" required pattern="[A-Za-z]{3}" maxLength={3} value={baseCurrency} onChange={(e) => setBaseCurrency(e.target.value)} />
          </label>
          <label>
            Total budget (optional)
            <input name="budget" type="number" min={0} step="0.01" value={budget} onChange={(e) => setBudget(e.target.value)} />
          </label>
          <label>
            Pace
            <select name="pace" value={pace} onChange={(e) => setPace(e.target.value as Pace)}>
              {PACES.map((p) => (
                <option key={p} value={p}>
                  {label(p)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <fieldset style={{ marginTop: 16 }}>
          <legend className="muted">Interests</legend>
          <div className="chips">
            {INTERESTS.map((i) => (
              <label key={i}>
                <input type="checkbox" checked={interests.includes(i)} onChange={() => setInterests((s) => toggle(s, i))} />
                {label(i)}
              </label>
            ))}
          </div>
        </fieldset>
        <fieldset style={{ marginTop: 16 }}>
          <legend className="muted">Dietary (always respected)</legend>
          <div className="chips">
            {DIETARY.map((d) => (
              <label key={d}>
                <input type="checkbox" checked={dietary.includes(d)} onChange={() => setDietary((s) => toggle(s, d))} />
                {label(d)}
              </label>
            ))}
          </div>
        </fieldset>
      </section>

      {error && (
        <div className="error" role="alert">
          <strong>{error.message}</strong>
          {error.details.length > 0 && (
            <ul>
              {error.details.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="actions">
        <button className="primary" type="submit" disabled={submitting}>
          {submitting ? "Creating…" : "Create trip"}
        </button>
      </div>
    </form>
  );
}
