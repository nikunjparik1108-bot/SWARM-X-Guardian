import { useState } from "react";
import EventStream from "../components/swarm/EventStream";

const KINDS = ["ALL", "TASK", "AUCTION", "NAV", "DELIVERY", "FAILURE", "RECOVERY", "NETWORK", "SAFETY", "BATTERY", "SYSTEM"];

export default function EventLogPage({ state }) {
  const [filter, setFilter] = useState("ALL");
  const events = (state.events || []).filter(e => filter === "ALL" || e.kind === filter);
  return (
    <>
      <div className="page-header">
        <div>
          <div className="eyebrow">/ EVENT LOG · SIMULATION AUDIT TRAIL</div>
          <h1>Every state transition, in order.</h1>
          <p>Each entry corresponds to a real change in the simulation. Filter by category.</p>
        </div>
        <div className="page-actions" data-testid="event-log-filters">
          {KINDS.map(k => (
            <button key={k} className={`btn ${filter === k ? "primary" : "ghost"}`} onClick={() => setFilter(k)} data-testid={`event-filter-${k}`}>{k}</button>
          ))}
        </div>
      </div>
      <div className="panel">
        <div className="panel-head"><div><span className="panel-kicker">STREAM</span><h2>{events.length} events</h2></div></div>
        <EventStream events={events} max={200} testId="event-log-stream" />
      </div>
    </>
  );
}
