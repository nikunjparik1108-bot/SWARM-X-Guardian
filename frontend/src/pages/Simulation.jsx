import { useState } from "react";
import { Pause, Play, RotateCcw, Siren, Wifi } from "lucide-react";
import { endpoints, NETWORK_STATES } from "../lib/api";

const SCENARIOS = [
  { id: "normal", label: "Baseline / normal" },
  { id: "agent_failure", label: "Agent failure" },
  { id: "multi_failure", label: "Multiple failures" },
  { id: "network_degradation", label: "Network degradation" },
  { id: "high_load", label: "High task load" },
  { id: "battery", label: "Battery depletion" },
  { id: "obstacle", label: "Dynamic obstacle" },
];

export default function SimulationPage({ state, command }) {
  const [scenario, setScenario] = useState("normal");
  const [agentCount, setAgentCount] = useState(state.agents.length || 12);
  const [mode, setMode] = useState(state.mode || "decentralized");

  const applyReset = () => command(() => endpoints.reset({ scenario, agent_count: agentCount, mode }));
  const setNetwork = (s) => command(() => endpoints.network(s));
  const toggle = () => command(endpoints.toggle);
  const injectFailure = async () => {
    const target = state.agents.find(a => a.task_id) || state.agents.find(a => a.status !== "FAILED");
    if (target) await command(() => endpoints.failAgent(target.id));
  };

  return (
    <>
      <div className="page-header">
        <div>
          <div className="eyebrow">/ SIMULATION · CONTROL SURFACE</div>
          <h1>Drive the swarm.</h1>
          <p>Inject failure, degrade the mesh, scale up. Every control triggers a real state transition in the simulation.</p>
        </div>
        <div className="page-actions">
          <button className="btn ghost" onClick={toggle} data-testid="simulation-toggle-button">
            {state.running ? <><Pause size={14} />Pause simulation</> : <><Play size={14} />Resume simulation</>}
          </button>
        </div>
      </div>

      <div className="split-2">
        <div className="panel">
          <div className="panel-head">
            <div>
              <span className="panel-kicker">SCENARIO</span>
              <h2>Reset & inject</h2>
            </div>
          </div>
          <div className="field">
            <label>Scenario</label>
            <select value={scenario} onChange={e => setScenario(e.target.value)} data-testid="scenario-select">
              {SCENARIOS.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
          </div>
          <div className="form-grid">
            <div className="field">
              <label>Agents</label>
              <input type="number" min="3" max="100" value={agentCount} onChange={e => setAgentCount(Number(e.target.value))} data-testid="agent-count-input" />
            </div>
            <div className="field">
              <label>Mode</label>
              <select value={mode} onChange={e => setMode(e.target.value)} data-testid="mode-select">
                <option value="decentralized">Decentralized</option>
                <option value="centralized">Centralized</option>
              </select>
            </div>
          </div>
          <button className="btn primary" onClick={applyReset} data-testid="scenario-apply-button">
            <RotateCcw size={14} /> Apply scenario
          </button>
          <button className="btn danger" style={{ marginTop: 12 }} onClick={injectFailure} data-testid="inject-failure-button">
            <Siren size={14} /> Inject agent failure
          </button>
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <span className="panel-kicker">NETWORK</span>
              <h2>Communication state</h2>
            </div>
            <span className="pill cyan"><i />{state.network_state}</span>
          </div>
          <p className="muted text-mono" style={{ fontSize: 12 }}>Alter link-quality profile to demonstrate degraded operation and recovery.</p>
          <div className="hstack" style={{ flexWrap: "wrap", gap: 8 }}>
            {NETWORK_STATES.map(s => (
              <button key={s} className={`btn ${state.network_state === s ? "primary" : "ghost"}`} onClick={() => setNetwork(s)} data-testid={`network-${s.toLowerCase()}`}>
                <Wifi size={13} /> {s.replaceAll("_", " ")}
              </button>
            ))}
          </div>
          <div style={{ marginTop: 20 }}>
            <div className="inspect-row"><span>Avg latency</span><b data-testid="sim-latency">{state.metrics.avg_latency_ms} ms</b></div>
            <div className="inspect-row"><span>Avg packet loss</span><b data-testid="sim-loss">{(state.metrics.avg_packet_loss * 100).toFixed(1)}%</b></div>
            <div className="inspect-row"><span>Connected pairs</span><b>{state.metrics.connected_pairs}</b></div>
            <div className="inspect-row"><span>Network partitions</span><b>{state.metrics.partitions}</b></div>
          </div>
        </div>
      </div>
    </>
  );
}
