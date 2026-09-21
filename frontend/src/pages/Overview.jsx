import { useState } from "react";
import { Link } from "react-router-dom";
import { Pause, Play, RotateCcw, ShieldCheck, Sparkles, Truck } from "lucide-react";
import { SwarmMap } from "../components/swarm/SwarmMap";
import AgentInspector from "../components/swarm/AgentInspector";
import EventStream from "../components/swarm/EventStream";
import { endpoints } from "../lib/api";

function Metric({ label, value, unit, tone, testId }) {
  return (
    <div className="metric-card" data-testid={testId}>
      <div className="label">{label}</div>
      <div className="value" style={{ color: tone || undefined }}>{value}<small>{unit}</small></div>
      <div className="foot sim">SIMULATION</div>
    </div>
  );
}

export default function Overview({ state, command, error }) {
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  const m = state.metrics;

  const toggle = () => command(endpoints.toggle);
  const reset = () => command(() => endpoints.reset({ scenario: "normal", agent_count: state.agents.length, mode: state.mode }));
  const failAgent = async (id) => {
    setBusy(true);
    await command(() => endpoints.failAgent(id));
    setSelected(null);
    setBusy(false);
  };

  return (
    <>
      <div className="page-header">
        <div>
          <div className="eyebrow">/ OVERVIEW · LIVE SWARM TELEMETRY</div>
          <h1>Decentralized intelligence. One resilient swarm.</h1>
          <p>
            An autonomous logistics simulation where individual agents coordinate locally,
            dynamically redistribute tasks, and adapt to failures without a central command center.
          </p>
        </div>
        <div className="page-actions">
          <Link className="btn ghost" to="/architecture" data-testid="overview-nav-architecture"><ShieldCheck size={14} />Architecture</Link>
          <Link className="btn ghost" to="/experiments" data-testid="overview-nav-experiments"><Truck size={14} />Experiments</Link>
          <Link className="btn primary" to="/judge" data-testid="overview-launch-judge"><Sparkles size={14} />Judge Mode</Link>
        </div>
      </div>

      <section className="metric-grid">
        <Metric label="ACTIVE AGENTS" value={m.active_agents} unit={` / ${state.agents.length}`} testId="metric-active" />
        <Metric label="FAILED AGENTS" value={m.failed_agents} tone="var(--red)" testId="metric-failed" />
        <Metric label="COMPLETED TASKS" value={m.completed_tasks} unit={` / ${m.total_tasks}`} testId="metric-completed" />
        <Metric label="AVG DELIVERY" value={m.avg_delivery_time} unit="s" testId="metric-delivery" />
        <Metric label="AVG RECOVERY" value={m.avg_recovery_time} unit="s" tone="var(--amber)" testId="metric-recovery" />
        <Metric label="NETWORK LATENCY" value={m.avg_latency_ms} unit="ms" testId="metric-latency" />
        <Metric label="PACKET LOSS" value={(m.avg_packet_loss * 100).toFixed(1)} unit="%" testId="metric-loss" />
        <Metric label="UTILIZATION" value={m.agent_utilization} unit="%" tone="var(--green)" testId="metric-util" />
      </section>

      <div className="split-2" style={{ marginBottom: 20 }}>
        <div className="panel">
          <div className="panel-head">
            <div>
              <span className="panel-kicker">LIVE FIELD</span>
              <h2>Mission topology</h2>
            </div>
            <div className="hstack">
              <button className="btn ghost" onClick={reset} data-testid="overview-reset-button"><RotateCcw size={13} />Reset</button>
              <button className="btn primary" onClick={toggle} data-testid="overview-toggle-button">
                {state.running ? <><Pause size={13} />Pause</> : <><Play size={13} />Resume</>}
              </button>
            </div>
          </div>
          <SwarmMap state={state} onSelect={setSelected} />
        </div>
        <div className="panel">
          <div className="panel-head">
            <div>
              <span className="panel-kicker">SELF-HEALING FEED</span>
              <h2>Recovery events</h2>
            </div>
            <span className="pill muted"><i />{state.events?.length || 0} events</span>
          </div>
          <EventStream events={state.events} max={20} testId="overview-events" />
        </div>
      </div>

      <div className="split-2">
        <div className="panel">
          <div className="panel-head">
            <div>
              <span className="panel-kicker">FLEET REGISTRY</span>
              <h2>Agent health</h2>
            </div>
            <span className="pill muted"><i />{state.agents.length} registered</span>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="table" data-testid="overview-agent-table">
              <thead><tr><th>AGENT</th><th>STATE</th><th>BATTERY</th><th>TASK</th><th>NEIGHBORS</th></tr></thead>
              <tbody>
                {state.agents.slice(0, 8).map(a => (
                  <tr key={a.id} onClick={() => setSelected(a)} style={{ cursor: "pointer" }} data-testid={`overview-agent-row-${a.id}`}>
                    <td className="mono">{a.id}</td>
                    <td><span className={`pill ${a.status === "FAILED" ? "red" : a.status === "DEGRADED" ? "blue" : a.status === "RETURNING" || a.status === "RECOVERING" ? "amber" : "green"}`}><i />{a.status}</span></td>
                    <td>{Math.round(a.battery)}%</td>
                    <td className="mono">{a.task_id || "—"}</td>
                    <td>{a.neighbors.length}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="panel">
          <div className="panel-head">
            <div>
              <span className="panel-kicker">TASK ALLOCATION</span>
              <h2>Mission queue</h2>
            </div>
            <span className="pill muted"><i />{m.pending_tasks} pending</span>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="table" data-testid="overview-task-table">
              <thead><tr><th>TASK</th><th>STATUS</th><th>PRIORITY</th><th>ASSIGNED</th></tr></thead>
              <tbody>
                {state.tasks.slice(0, 8).map(t => (
                  <tr key={t.id} data-testid={`overview-task-row-${t.id}`}>
                    <td className="mono">{t.id}</td>
                    <td><span className={`pill ${t.status === "DELIVERED" ? "green" : t.status === "INTERRUPTED" ? "red" : t.status === "AUCTIONING" ? "blue" : "cyan"}`}><i />{t.status}</span></td>
                    <td>{t.priority}</td>
                    <td className="mono">{t.assigned_agent || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {selected && <AgentInspector agent={selected} onClose={() => setSelected(null)} onFail={failAgent} />}
    </>
  );
}
