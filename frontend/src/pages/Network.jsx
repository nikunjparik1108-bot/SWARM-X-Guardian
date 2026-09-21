import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { NETWORK_STATES, endpoints } from "../lib/api";
import { useEffect, useState } from "react";

export default function NetworkPage({ state, command }) {
  const [samples, setSamples] = useState([]);
  useEffect(() => {
    if (!state) return;
    setSamples(prev => [...prev.slice(-40), {
      tick: state.tick,
      latency: state.metrics.avg_latency_ms,
      loss: state.metrics.avg_packet_loss * 100,
      pairs: state.metrics.connected_pairs,
    }]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.tick]);

  const setNetwork = (s) => command(() => endpoints.network(s));

  return (
    <div data-testid="network-page">
      <div className="page-header">
        <div>
          <div className="eyebrow">/ NETWORK · COMMUNICATION MESH</div>
          <h1>Peer-to-peer, degraded, or partitioned.</h1>
          <p>Every link tracks latency, packet loss, and signal quality. Agents adapt locally when the mesh drops.</p>
        </div>
        <div className="page-actions">
          {NETWORK_STATES.map(s => (
            <button key={s} className={`btn ${state.network_state === s ? "primary" : "ghost"}`} onClick={() => setNetwork(s)} data-testid={`network-page-${s.toLowerCase()}`}>
              {s.replaceAll("_", " ")}
            </button>
          ))}
        </div>
      </div>

      <div className="metric-grid">
        <div className="metric-card" data-testid="net-latency"><div className="label">AVG LATENCY</div><div className="value">{state.metrics.avg_latency_ms}<small>ms</small></div><div className="foot sim">LIVE MESH</div></div>
        <div className="metric-card" data-testid="net-loss"><div className="label">PACKET LOSS</div><div className="value" style={{ color: state.metrics.avg_packet_loss > 0.2 ? "var(--red)" : undefined }}>{(state.metrics.avg_packet_loss * 100).toFixed(1)}<small>%</small></div><div className="foot sim">LIVE MESH</div></div>
        <div className="metric-card"><div className="label">CONNECTED PAIRS</div><div className="value">{state.metrics.connected_pairs}</div><div className="foot sim">LIVE MESH</div></div>
        <div className="metric-card"><div className="label">PARTITIONS</div><div className="value" style={{ color: state.metrics.partitions > 1 ? "var(--amber)" : undefined }}>{state.metrics.partitions}</div><div className="foot sim">LIVE MESH</div></div>
      </div>

      <div className="split-2">
        <div className="panel">
          <div className="panel-head"><div><span className="panel-kicker">HISTORICAL</span><h2>Latency & loss over ticks</h2></div></div>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={samples} data-testid="network-history-chart">
              <CartesianGrid stroke="#232a34" strokeDasharray="3 3" />
              <XAxis dataKey="tick" stroke="#8c95a1" tick={{ fontSize: 10 }} />
              <YAxis stroke="#8c95a1" tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ background: "#141920", border: "1px solid #303844", color: "#eef1f5" }} />
              <Line type="monotone" dataKey="latency" stroke="#35c8d1" strokeWidth={2} dot={false} name="Latency (ms)" />
              <Line type="monotone" dataKey="loss" stroke="#ff5c4d" strokeWidth={2} dot={false} name="Loss (%)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="panel">
          <div className="panel-head"><div><span className="panel-kicker">LINKS</span><h2>Peer connections</h2></div><span className="pill muted"><i />{state.links.length}</span></div>
          <div style={{ maxHeight: 320, overflowY: "auto" }}>
            <table className="table" data-testid="network-links-table">
              <thead><tr><th>PAIR</th><th>LATENCY</th><th>LOSS</th><th>SIGNAL</th></tr></thead>
              <tbody>
                {state.links.slice(0, 40).map((l, i) => (
                  <tr key={`${l.a}-${l.b}`} data-testid={`network-link-${i}`}>
                    <td className="mono">{l.a} ↔ {l.b}</td>
                    <td>{l.latency} ms</td>
                    <td>{(l.loss * 100).toFixed(1)}%</td>
                    <td>{(l.signal * 100).toFixed(0)}%</td>
                  </tr>
                ))}
                {state.links.length === 0 && <tr><td colSpan={4} className="muted text-mono">Mesh disconnected.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
