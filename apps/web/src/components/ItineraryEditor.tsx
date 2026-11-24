"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  ApiRequestError,
  addItem,
  deleteItem,
  generateItinerary,
  getItinerary,
  getTrip,
  lockItem,
  regenerateDay,
} from "../lib/api";
import { shortDate } from "../lib/format";
import { PACES, label } from "../lib/options";
import type { PlanDay, PlanItem, PlanVersion, RegenerateRequest, Trip } from "../types";

type Problem = { message: string; details: string[] };

function hhmm(iso: string, timeZone: string): string {
  return new Intl.DateTimeFormat("en-GB", { timeZone, hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(new Date(iso));
}

function localDate(iso: string, timeZone: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone }).format(new Date(iso)); // YYYY-MM-DD
}

function dayLabel(isoDate: string): string {
  return new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" }).format(
    new Date(`${isoDate}T00:00:00Z`),
  );
}

function DiffSummary({ plan }: { plan: PlanVersion }) {
  const d = plan.diff;
  if (!d || d.from_version == null) return null;
  const parts = [
    d.added.length && `+${d.added.length} added`,
    d.removed.length && `−${d.removed.length} removed`,
    d.changed.length && `${d.changed.length} changed`,
  ].filter(Boolean);
  return (
    <p className="muted" data-testid="diff-summary">
      Since v{d.from_version}: {parts.length ? parts.join(", ") : "no changes"}
      {d.changed_dates.length > 0 && ` · ${d.changed_dates.map(shortDate).join(", ")}`} · {d.unchanged} unchanged
    </p>
  );
}

function ItemRow({ item, day, busy, onLock, onRemove }: {
  item: PlanItem;
  day: PlanDay;
  busy: boolean;
  onLock: (item: PlanItem) => void;
  onRemove: (item: PlanItem) => void;
}) {
  const isBooking = item.kind === "booking";
  return (
    <li className={`item item-${item.kind}`} data-testid="plan-item">
      <span className="time">
        {hhmm(item.starts_at, day.timezone)}–{hhmm(item.ends_at, day.timezone)}
        {localDate(item.ends_at, day.timezone) > day.date && <sup title="next day"> +1</sup>}
      </span>
      <span className="what">
        <strong>{item.title}</strong> <span className="tag">{isBooking ? "booking" : label(item.kind)}</span>
        {item.locked && !isBooking && <span className="tag">locked</span>}
        {item.source === "user" && <span className="tag">yours</span>}
        {item.why && <span className="why muted">{item.why}</span>}
      </span>
      {!isBooking && (
        <span className="item-actions">
          <button type="button" disabled={busy} onClick={() => onLock(item)} aria-label={`${item.locked ? "Unlock" : "Lock"} ${item.title}`}>
            {item.locked ? "Unlock" : "Lock"}
          </button>
          <button type="button" disabled={busy || item.locked} onClick={() => onRemove(item)} aria-label={`Remove ${item.title}`}>
            Remove
          </button>
        </span>
      )}
    </li>
  );
}

function DayCard({ day, trip, busy, run }: {
  day: PlanDay;
  trip: Trip;
  busy: boolean;
  run: (action: () => Promise<PlanVersion>) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [replanning, setReplanning] = useState(false);
  const [title, setTitle] = useState("");
  const [start, setStart] = useState("10:00");
  const [end, setEnd] = useState("11:00");
  const [pace, setPace] = useState("");
  const [radius, setRadius] = useState("");
  const [drop, setDrop] = useState<string[]>([]);
  const [note, setNote] = useState("");
  const stop = trip.stops[day.stop_seq];
  const userItems = day.items.filter((i) => i.source === "user" && !i.locked);

  function submitAdd(e: FormEvent) {
    e.preventDefault();
    run(() => addItem(trip.id, { date: day.date, title, start, end }));
    setAdding(false);
    setTitle("");
  }

  function submitReplan(e: FormEvent) {
    e.preventDefault();
    run(() =>
      regenerateDay(trip.id, {
        scope: { date: day.date },
        remove_item_keys: drop,
        exclude_place_ids: [],
        stay_within_m: radius ? Number(radius) : null,
        pace: (pace || null) as RegenerateRequest["pace"],
        note,
      }),
    );
    setReplanning(false);
    setDrop([]);
    setNote("");
  }

  return (
    <section className="card" aria-label={`Day ${day.date}`} data-testid={`day-${day.date}`}>
      <h2>
        {dayLabel(day.date)} · {stop?.city ?? "—"}
      </h2>
      {day.items.length ? (
        <ul className="items">
          {day.items.map((item) => (
            <ItemRow
              key={item.item_key}
              item={item}
              day={day}
              busy={busy}
              onLock={(i) => run(() => lockItem(trip.id, i.item_key, !i.locked))}
              onRemove={(i) => run(() => deleteItem(trip.id, i.item_key))}
            />
          ))}
        </ul>
      ) : (
        <p className="muted">Nothing planned — no free time this day.</p>
      )}

      <div className="row" style={{ marginTop: 12 }}>
        <button type="button" disabled={busy} onClick={() => { setAdding(!adding); setReplanning(false); }}>
          Add item
        </button>
        <button type="button" disabled={busy} onClick={() => { setReplanning(!replanning); setAdding(false); }}>
          Re-plan this day
        </button>
      </div>

      {adding && (
        <form className="row" style={{ marginTop: 12 }} onSubmit={submitAdd} aria-label={`Add item on ${day.date}`}>
          <label>
            Title
            <input required maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label style={{ flex: "0 1 120px" }}>
            Start
            <input type="time" required value={start} onChange={(e) => setStart(e.target.value)} />
          </label>
          <label style={{ flex: "0 1 120px" }}>
            End
            <input type="time" required value={end} onChange={(e) => setEnd(e.target.value)} />
          </label>
          <button className="primary" type="submit" disabled={busy}>
            Add
          </button>
        </form>
      )}

      {replanning && (
        <form style={{ marginTop: 12 }} onSubmit={submitReplan} aria-label={`Re-plan ${day.date}`}>
          <p className="muted hint">Bookings, locked items and every other day stay exactly as they are.</p>
          <div className="grid">
            <label>
              Pace
              <select value={pace} onChange={(e) => setPace(e.target.value)}>
                <option value="">Keep trip pace</option>
                {PACES.map((p) => (
                  <option key={p} value={p}>
                    {label(p)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Stay near the centre
              <select value={radius} onChange={(e) => setRadius(e.target.value)}>
                <option value="">Anywhere</option>
                <option value="1000">Within 1 km</option>
                <option value="3000">Within 3 km</option>
                <option value="5000">Within 5 km</option>
              </select>
            </label>
            <label>
              Reason (saved with the version)
              <input maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Remove Aswan" />
            </label>
          </div>
          {userItems.length > 0 && (
            <fieldset style={{ marginTop: 12 }}>
              <legend className="muted">Drop your items</legend>
              <div className="chips">
                {userItems.map((i) => (
                  <label key={i.item_key}>
                    <input
                      type="checkbox"
                      checked={drop.includes(i.item_key)}
                      onChange={() => setDrop((d) => (d.includes(i.item_key) ? d.filter((k) => k !== i.item_key) : [...d, i.item_key]))}
                    />
                    {i.title}
                  </label>
                ))}
              </div>
            </fieldset>
          )}
          <div className="actions">
            <button className="primary" type="submit" disabled={busy}>
              Re-plan {dayLabel(day.date)}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

export function ItineraryEditor({ tripId }: { tripId: string }) {
  const [trip, setTrip] = useState<Trip | null>(null);
  const [plan, setPlan] = useState<PlanVersion | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<Problem | null>(null);

  useEffect(() => {
    Promise.all([getTrip(tripId), getItinerary(tripId)])
      .then(([t, p]) => {
        setTrip(t);
        setPlan(p);
      })
      .catch((err) => setProblem({ message: err instanceof ApiRequestError && err.status === 404 ? "Trip not found." : err.message, details: [] }));
  }, [tripId]);

  const run = useCallback((action: () => Promise<PlanVersion>) => {
    setBusy(true);
    setProblem(null);
    action()
      .then(setPlan)
      .catch((err) =>
        setProblem(err instanceof ApiRequestError ? { message: err.message, details: err.details } : { message: "Could not reach the API.", details: [] }),
      )
      .finally(() => setBusy(false));
  }, []);

  if (!trip) {
    return problem ? <div className="error" role="alert">{problem.message}</div> : <p className="muted">Loading…</p>;
  }

  const warnings = plan?.warnings ?? [];
  return (
    <article>
      <p>
        <a href={`/trips/${trip.id}`}>← {trip.title}</a>
      </p>
      <h1>Itinerary</h1>
      {plan ? (
        <>
          <p className="muted" data-testid="version">
            Version {plan.version} · {plan.created_by === "user" ? "your edit" : `planned (${plan.planner})`}
            {plan.reason && ` · ${plan.reason}`}
          </p>
          <DiffSummary plan={plan} />
          {plan.explanation && <p className="hint">{plan.explanation}</p>}
        </>
      ) : (
        plan === null && <p className="muted">No itinerary yet. Generate one from your stops, bookings and preferences.</p>
      )}

      <div className="actions">
        <button className="primary" type="button" disabled={busy} onClick={() => run(() => generateItinerary(trip.id))}>
          {plan ? "Re-plan whole trip" : "Generate itinerary"}
        </button>
      </div>

      {problem && (
        <div className="error" role="alert">
          <strong>{problem.message}</strong>
          {problem.details.length > 0 && (
            <ul>
              {problem.details.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {warnings.length > 0 && (
        <div className="card warn" data-testid="warnings">
          <strong>Check before you go</strong>
          <ul>
            {warnings.map((w, i) => (
              <li key={i}>
                {w.date ? `${shortDate(w.date)}: ` : ""}
                {w.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {plan?.days.map((day) => <DayCard key={day.date} day={day} trip={trip} busy={busy} run={run} />)}
    </article>
  );
}
