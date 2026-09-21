import { X, Siren } from "lucide-react";
import { AGENT_STATUS_TONE } from "../../lib/api";

function Stat({ label, value, unit }) {
  return (
    <div className="metric-card" style={{ padding: 12 }}>
      <div className="label">{label}</div>
      <div className="value" style={{ fontSize: 20 }}>{value}<small>{unit || ""}</small></div>
    </div>
  );
}

export default function AgentInspector({ agent, onClose, onFail }) {
  if (!agent) return null;
  const tone = AGENT_STATUS_TONE[agent.status] || "muted";
  const factors = agent.decision_factors || {};
  return (
    <div className="inspector-overlay" onClick={onClose} data-testid="agent-inspector-overlay">
      <aside className="inspector-panel" onClick={e => e.stopPropagation()} data-testid="agent-inspector">
        <button className="btn ghost" onClick={onClose} data-testid="close-inspector-button" style={{ float: "right" }}><X size={14} /> Close</button>
        <span className="panel-kicker">AGENT INSPECTOR</span>
        <h2>{agent.id}</h2>
        <div className="hstack" style={{ marginBottom: 6 }}>
          <span className={`pill ${tone}`} data-testid="inspector-status"><i />{agent.status}</span>
          <span className="pill muted"><i />HEALTH · {agent.health}</span>
          <span className="pill muted"><i />RISK · {agent.risk_level}</span>
        </div>
        <div className="inspector-stats">
          <Stat label="BATTERY" value={Math.round(agent.battery)} unit="%" />
          <Stat label="SPEED" value={Math.round(agent.speed)} unit=" km/h" />
          <Stat label="NEIGHBORS" value={agent.neighbors?.length ?? 0} />
        </div>
        <div className="inspect-row"><span>Current task</span><b data-testid="inspector-task">{agent.task_id || "—"}</b></div>
        <div className="inspect-row"><span>Payload</span><b>{agent.current_payload} / {agent.payload_capacity} kg</b></div>
        <div className="inspect-row"><span>Position</span><b>{Math.round(agent.x)} · {Math.round(agent.y)}</b></div>
        <div className="inspect-row"><span>Comm quality</span><b>{Math.round((agent.comm_quality ?? 0) * 100)}%</b></div>
        <div className="inspect-row"><span>Delivered</span><b>{agent.delivered_count}</b></div>
        <div className="inspect-row"><span>Recoveries</span><b>{agent.recovered_count}</b></div>

        <div style={{ margin: "18px 0 8px" }}>
          <span className="panel-kicker">CURRENT DECISION FACTORS</span>
        </div>
        {factors.eligible === false && <div className="muted text-mono">Not eligible: {factors.reason || "n/a"}</div>}
        {factors.eligible !== false && (
          <div>
            <div className="inspect-row"><span>Local task score</span><b data-testid="inspector-score">{factors.score ?? "—"}</b></div>
            <div className="inspect-row"><span>Distance ({factors.distance_km} km)</span><b>{factors.distance || "—"}</b></div>
            <div className="inspect-row"><span>Battery</span><b>{factors.battery || "—"}</b></div>
            <div className="inspect-row"><span>Payload</span><b>{factors.payload || "—"}</b></div>
            <div className="inspect-row"><span>ETA ({factors.eta_s} s)</span><b>{factors.eta || "—"}</b></div>
            <div className="inspect-row"><span>Workload</span><b>{factors.workload || "—"}</b></div>
            <div className="inspect-row"><span>Priority</span><b>{factors.priority || "—"}</b></div>
          </div>
        )}

        {agent.status !== "FAILED" && (
          <button
            className="btn danger"
            style={{ marginTop: 22, width: "100%", justifyContent: "center" }}
            onClick={() => onFail?.(agent.id)}
            data-testid="inspector-fail-button"
          >
            <Siren size={14} /> Simulate agent failure
          </button>
        )}
      </aside>
    </div>
  );
}
