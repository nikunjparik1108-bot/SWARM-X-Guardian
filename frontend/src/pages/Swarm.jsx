import { useState } from "react";
import { SwarmMap } from "../components/swarm/SwarmMap";
import AgentInspector from "../components/swarm/AgentInspector";
import { endpoints } from "../lib/api";

export default function Swarm({ state, command }) {
  const [selected, setSelected] = useState(null);
  const [showLinks, setShowLinks] = useState(true);

  const failAgent = async (id) => {
    await command(() => endpoints.failAgent(id));
    setSelected(null);
  };

  return (
    <>
      <div className="page-header">
        <div>
          <div className="eyebrow">/ SWARM · TOPOLOGY & AGENTS</div>
          <h1>The fleet in flight.</h1>
          <p>Each agent maintains local state, discovers its neighbors, and negotiates task assignment through the mesh.</p>
        </div>
        <div className="page-actions">
          <label className="btn ghost" data-testid="swarm-links-toggle">
            <input type="checkbox" checked={showLinks} onChange={e => setShowLinks(e.target.checked)} style={{ accentColor: "var(--accent)" }} /> Mesh links
          </label>
        </div>
      </div>

      <div className="split-2" style={{ marginBottom: 20 }}>
        <div className="panel">
          <div className="panel-head">
            <div>
              <span className="panel-kicker">LIVE TOPOLOGY</span>
              <h2>Peer-to-peer mesh</h2>
            </div>
            <span className="pill muted"><i />{state.links.length} links · {state.metrics.partitions} partition{state.metrics.partitions !== 1 ? "s" : ""}</span>
          </div>
          <SwarmMap state={state} onSelect={setSelected} showLinks={showLinks} />
        </div>
        <div className="panel">
          <div className="panel-head">
            <div>
              <span className="panel-kicker">FLEET REGISTRY</span>
              <h2>{state.agents.length} agents</h2>
            </div>
          </div>
          <div style={{ maxHeight: 520, overflowY: "auto" }}>
            <table className="table" data-testid="swarm-agent-table">
              <thead><tr><th>ID</th><th>STATE</th><th>BATT</th><th>COMM</th><th>NBR</th></tr></thead>
              <tbody>
                {state.agents.map(a => (
                  <tr key={a.id} onClick={() => setSelected(a)} style={{ cursor: "pointer" }} data-testid={`swarm-agent-row-${a.id}`}>
                    <td className="mono">{a.id}</td>
                    <td><span className={`pill ${a.status === "FAILED" ? "red" : a.status === "DEGRADED" ? "blue" : a.status === "RETURNING" || a.status === "RECOVERING" ? "amber" : "green"}`}><i />{a.status}</span></td>
                    <td>{Math.round(a.battery)}%</td>
                    <td>{Math.round((a.comm_quality ?? 0) * 100)}%</td>
                    <td>{a.neighbors.length}</td>
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
