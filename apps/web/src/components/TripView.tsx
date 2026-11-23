"use client";

import { useEffect, useState } from "react";

import { ApiRequestError, getTrip } from "../lib/api";
import { localTime, money, shortDate } from "../lib/format";
import { label } from "../lib/options";
import type { Constraint, Trip } from "../types";

/** Timezone of the stop the instant falls in (by UTC date), else the first stop's. */
function stopTimezone(trip: Trip, iso: string, seq?: number | null): string | null | undefined {
  if (seq != null) return trip.stops[seq]?.timezone;
  const day = iso.slice(0, 10);
  const stop = trip.stops.find((s) => s.arrive_on <= day && day <= s.leave_on) ?? trip.stops[0];
  return stop?.timezone;
}

function describeConstraint(trip: Trip, c: Constraint): string {
  if (c.kind === "must_do") return `Must do: ${c.query ?? c.place_id}${c.on_date ? ` (${shortDate(c.on_date)})` : ""}`;
  if (c.kind === "avoid") return `Avoid: ${c.query ?? c.category}`;
  const tz = stopTimezone(trip, c.starts_at);
  return `${c.label}: ${localTime(c.starts_at, tz)} – ${localTime(c.ends_at, tz)}`;
}

export function TripView({ id }: { id: string }) {
  const [trip, setTrip] = useState<Trip | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTrip(id)
      .then(setTrip)
      .catch((err) => setError(err instanceof ApiRequestError && err.status === 404 ? "Trip not found." : err.message));
  }, [id]);

  if (error) return <div className="error" role="alert">{error}</div>;
  if (!trip) return <p className="muted">Loading trip…</p>;

  const party = [
    `${trip.adults} adult${trip.adults === 1 ? "" : "s"}`,
    trip.children_ages.length ? `${trip.children_ages.length} child (${trip.children_ages.join(", ")})` : null,
    trip.infants ? `${trip.infants} infant${trip.infants === 1 ? "" : "s"}` : null,
  ].filter(Boolean);

  return (
    <article>
      <h1>{trip.title}</h1>
      <p className="muted">
        {trip.origin} · {shortDate(trip.start_date)} – {shortDate(trip.end_date)} · <span className="tag">{trip.status}</span>
      </p>

      <section className="card">
        <h2>Overview</h2>
        <dl className="facts">
          <dt>Travellers</dt>
          <dd data-testid="travellers">
            {trip.travellers} ({party.join(", ")})
          </dd>
          <dt>Pace</dt>
          <dd>{label(trip.pace)}</dd>
          <dt>Day window</dt>
          <dd>
            {trip.day_window.start.slice(0, 5)}–{trip.day_window.end.slice(0, 5)}
          </dd>
          <dt>Currency</dt>
          <dd>
            {trip.base_currency}
            {trip.settlement_currency !== trip.base_currency && ` (settle in ${trip.settlement_currency})`}
          </dd>
          <dt>Budget</dt>
          <dd>{trip.budget ? `${money(trip.budget.total)} ${label(trip.budget.scope)}` : "—"}</dd>
          <dt>Mobility</dt>
          <dd>{label(trip.mobility_needs)}</dd>
          <dt>Interests</dt>
          <dd>{trip.interests.length ? trip.interests.map((i) => <span className="tag" key={i}>{label(i)}</span>) : "—"}</dd>
          <dt>Dietary</dt>
          <dd>{trip.dietary.length ? trip.dietary.map((d) => <span className="tag" key={d}>{label(d)}</span>) : "—"}</dd>
        </dl>
      </section>

      <section className="card">
        <h2>Stops</h2>
        <div className="scroll">
          <table aria-label="Stops">
            <thead>
              <tr><th>#</th><th>City</th><th>Nights</th><th>Dates</th><th>Stay</th></tr>
            </thead>
            <tbody>
              {trip.stops.map((s) => (
                <tr key={s.id}>
                  <td>{s.seq + 1}</td>
                  <td>{s.city}</td>
                  <td>{s.nights}</td>
                  <td>{shortDate(s.arrive_on)} – {shortDate(s.leave_on)}</td>
                  <td>{s.accommodation_area ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2>Members</h2>
        {trip.members.length ? (
          <ul>{trip.members.map((m) => <li key={m.id}>{m.display_name} <span className="muted">· {m.role}</span></li>)}</ul>
        ) : (
          <p className="muted">No members yet.</p>
        )}
      </section>

      <section className="card">
        <h2>Constraints</h2>
        {trip.constraints.length ? (
          <ul>
            {trip.constraints.map((c) => (
              <li key={c.id}>
                {describeConstraint(trip, c)} <span className="tag">{c.hardness}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No constraints.</p>
        )}
      </section>

      <section className="card">
        <h2>Bookings</h2>
        {trip.bookings.length ? (
          <div className="scroll">
            <table aria-label="Bookings">
              <thead>
                <tr><th>When (local)</th><th>What</th><th>Kind</th><th>Cost</th><th>Status</th></tr>
              </thead>
              <tbody>
                {trip.bookings.map((b) => (
                  <tr key={b.id}>
                    <td>{localTime(b.starts_at, stopTimezone(trip, b.starts_at, b.stop_seq))}</td>
                    <td>{b.title}</td>
                    <td>{label(b.kind)}</td>
                    <td>{b.cost ? money(b.cost) : "—"}</td>
                    <td>{b.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">No bookings yet.</p>
        )}
      </section>

      <p style={{ marginTop: 24 }}>
        <a href="/">Create another trip</a>
      </p>
    </article>
  );
}
