import { useState } from "react";

const LAYERS = [
  {
    id: "mission", title: "Mission Layer",
    purpose: "Define delivery goals, priorities, deadlines, and payload constraints.",
    inputs: ["User-defined tasks", "Scheduled operations", "External work orders"],
    outputs: ["Task specifications", "Priority weights"],
    responsibilities: ["Task lifecycle ownership", "SLA policy", "Priority arbitration"],
  },
  {
    id: "coordination", title: "Task / Coordination Layer",
    purpose: "Announce tasks to the swarm and orchestrate the auction / negotiation.",
    inputs: ["Task specifications", "Peer bids"],
    outputs: ["Assignment decisions", "Bid ledgers", "Reassignment triggers"],
    responsibilities: ["Auction rounds", "Winner selection", "Interruption handling"],
  },
  {
    id: "agent", title: "Agent Decision Layer",
    purpose: "Score tasks locally using a transparent utility function.",
    inputs: ["Local state", "Task announcement", "Neighbor context"],
    outputs: ["Bid score + decision factors", "Route plan"],
    responsibilities: ["State machine progression", "Local optimization", "Self-preservation"],
  },
  {
    id: "mesh", title: "P2P Communication Layer",
    purpose: "Distance-based neighbor discovery and heartbeat monitoring.",
    inputs: ["Broadcast messages", "Physical proximity"],
    outputs: ["Neighbor set", "Link quality metrics", "Timeout events"],
    responsibilities: ["Heartbeat gossip", "Link attenuation model", "Partition detection"],
  },
  {
    id: "safety", title: "Safety / Constraint Layer",
    purpose: "Enforce minimum separation and detect route conflicts.",
    inputs: ["Agent positions", "Planned routes"],
    outputs: ["Route recalculations", "Near-miss / collision events"],
    responsibilities: ["Separation enforcement", "Route deconfliction (simulated)", "Event auditing"],
    note: "SIMULATED SAFETY MODEL — not an aviation certification.",
  },
  {
    id: "environment", title: "Simulation Environment",
    purpose: "Advance world state and expose observable snapshots.",
    inputs: ["Layered decisions", "External API commands"],
    outputs: ["World snapshot", "Metrics", "Event log"],
    responsibilities: ["Tick loop", "State persistence", "Observability"],
  },
];

export default function ArchitecturePage() {
  const [openId, setOpenId] = useState("agent");
  const open = LAYERS.find(l => l.id === openId);

  return (
    <>
      <div className="page-header">
        <div>
          <div className="eyebrow">/ ARCHITECTURE · SYSTEM MODEL</div>
          <h1>How intelligence is distributed.</h1>
          <p>Six layers, one operational spine. Click a layer to inspect its contract.</p>
        </div>
      </div>

      <div className="split-2">
        <div>
          {LAYERS.map(layer => (
            <button
              key={layer.id}
              className={`arch-layer ${layer.id === openId ? "active" : ""}`}
              onClick={() => setOpenId(layer.id)}
              data-testid={`arch-layer-${layer.id}`}
            >
              <div>
                <h3>{layer.title}</h3>
                <p>{layer.purpose}</p>
              </div>
              <span className="pill muted" style={{ flexShrink: 0 }}><i />OPEN</span>
            </button>
          ))}
        </div>
        <div className="panel" data-testid="arch-detail">
          <span className="panel-kicker">LAYER DETAIL</span>
          <h2>{open.title}</h2>
          {open.note && <p style={{ color: "var(--amber)" }} className="text-mono">{open.note}</p>}
          <p className="muted">{open.purpose}</p>
          <div style={{ marginTop: 18 }}>
            <span className="panel-kicker">INPUTS</span>
            <ul className="muted" style={{ paddingLeft: 18 }}>{open.inputs.map(i => <li key={i}>{i}</li>)}</ul>
          </div>
          <div style={{ marginTop: 12 }}>
            <span className="panel-kicker">OUTPUTS</span>
            <ul className="muted" style={{ paddingLeft: 18 }}>{open.outputs.map(i => <li key={i}>{i}</li>)}</ul>
          </div>
          <div style={{ marginTop: 12 }}>
            <span className="panel-kicker">RESPONSIBILITIES</span>
            <ul className="muted" style={{ paddingLeft: 18 }}>{open.responsibilities.map(i => <li key={i}>{i}</li>)}</ul>
          </div>
        </div>
      </div>
    </>
  );
}
