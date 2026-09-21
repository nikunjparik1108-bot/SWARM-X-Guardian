import { useEffect, useState } from "react";
import { Download, Play, RefreshCw, Scale } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { endpoints } from "../lib/api";

const COLS = [
  { key: "completion_rate", label: "Completion %" },
  { key: "avg_delivery_time", label: "Avg delivery (s)" },
  { key: "avg_recovery_time", label: "Avg recovery (s)" },
  { key: "route_changes", label: "Route changes" },
  { key: "safety_events", label: "Safety events" },
  { key: "utilization", label: "Utilization %" },
  { key: "coordination_cost", label: "Coord. cost" },
  { key: "recovered_tasks", label: "Recovered" },
];

function toCsv(rows) {
  const header = ["run_id", "scenario", "mode", "agents", "completed", "pending", "failures",
                  "recovered_tasks", "avg_delivery_time", "avg_recovery_time",
                  "route_changes", "safety_events", "completion_rate", "utilization",
                  "coordination_cost", "mission_duration_s"].join(",");
  const body = rows.map(r => [r.id, r.scenario, r.mode, r.agent_count, r.completed, r.pending,
                              r.failures, r.recovered_tasks, r.avg_delivery_time, r.avg_recovery_time,
                              r.route_changes, r.safety_events, r.completion_rate, r.utilization,
                              r.coordination_cost, r.mission_duration_s].join(","));
  return [header, ...body].join("\n");
}

export default function Experiments() {
  const [scenarios, setScenarios] = useState([]);
  const [scenarioId, setScenarioId] = useState("baseline");
  const [mode, setMode] = useState("decentralized");
  const [agentCount, setAgentCount] = useState(12);
  const [results, setResults] = useState([]);
  const [compare, setCompare] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    endpoints.experimentScenarios()
      .then(d => setScenarios(d.scenarios))
      .catch(() => setError("Cannot load scenarios"));
  }, []);

  const run = async () => {
    setBusy(true); setError("");
    try {
      const r = await endpoints.runExperiment({ scenario: scenarioId, mode, agent_count: agentCount });
      r.__key = `${r.id || "exp"}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
      setResults(prev => [r, ...prev].slice(0, 20));
    } catch (e) { setError("Experiment failed"); }
    finally { setBusy(false); }
  };

  const runCompare = async () => {
    setBusy(true); setError("");
    try {
      const r = await endpoints.compareExperiment({ scenario: scenarioId });
      setCompare(r);
      const dec = { ...r.decentralized, __key: `dec-${Date.now()}-${Math.random().toString(36).slice(2, 6)}` };
      const cen = { ...r.centralized, __key: `cen-${Date.now()}-${Math.random().toString(36).slice(2, 6)}` };
      setResults(prev => [dec, cen, ...prev].slice(0, 20));
    } catch (e) { setError("Comparison failed"); }
    finally { setBusy(false); }
  };

  const download = () => {
    if (!results.length) return;
    const blob = new Blob([toCsv(results)], { type: "text/csv" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `swarm-x-experiments.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const chartData = compare ? [
    { metric: "Completion %", centralized: compare.centralized.completion_rate, decentralized: compare.decentralized.completion_rate },
    { metric: "Delivery s", centralized: compare.centralized.avg_delivery_time, decentralized: compare.decentralized.avg_delivery_time },
    { metric: "Recovery s", centralized: compare.centralized.avg_recovery_time, decentralized: compare.decentralized.avg_recovery_time },
    { metric: "Safety evt", centralized: compare.centralized.safety_events, decentralized: compare.decentralized.safety_events },
    { metric: "Recovered", centralized: compare.centralized.recovered_tasks, decentralized: compare.decentralized.recovered_tasks },
  ] : null;

  return (
    <>
      <div className="page-header">
        <div>
          <div className="eyebrow">/ EXPERIMENTS · MEASURED RESULTS</div>
          <h1>Run it. Measure it. Compare it.</h1>
          <p>Each experiment executes a deterministic simulation and records real metrics. Results are directly comparable between centralized and decentralized coordination under identical seeds.</p>
        </div>
        <div className="page-actions">
          <button className="btn ghost" onClick={download} disabled={!results.length} data-testid="experiments-export-button">
            <Download size={14} /> Export CSV
          </button>
        </div>
      </div>

      <div className="split-2" style={{ marginBottom: 20 }}>
        <div className="panel">
          <div className="panel-head"><div><span className="panel-kicker">CONFIGURATION</span><h2>Run experiment</h2></div></div>
          <div className="field">
            <label>Scenario</label>
            <select value={scenarioId} onChange={e => setScenarioId(e.target.value)} data-testid="experiments-scenario-select">
              {scenarios.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
          </div>
          <div className="form-grid">
            <div className="field">
              <label>Mode</label>
              <select value={mode} onChange={e => setMode(e.target.value)} data-testid="experiments-mode-select">
                <option value="decentralized">Decentralized</option>
                <option value="centralized">Centralized</option>
              </select>
            </div>
            <div className="field">
              <label>Agents</label>
              <input type="number" min="3" max="100" value={agentCount} onChange={e => setAgentCount(Number(e.target.value))} data-testid="experiments-agent-count" />
            </div>
          </div>
          <div className="hstack">
            <button className="btn primary" onClick={run} disabled={busy} data-testid="experiments-run-button">
              {busy ? <RefreshCw size={14} className="mono" /> : <Play size={14} />} Run
            </button>
            <button className="btn ghost" onClick={runCompare} disabled={busy} data-testid="experiments-compare-button">
              <Scale size={14} /> Central vs Decentralized
            </button>
          </div>
          {error && <div className="muted" style={{ marginTop: 12, color: "var(--red)" }}>{error}</div>}
          <p className="muted text-mono" style={{ fontSize: 11, marginTop: 14 }}>SIMULATION · results derived from real ticks, not hard-coded numbers.</p>
        </div>
        <div className="panel">
          <div className="panel-head"><div><span className="panel-kicker">COMPARISON</span><h2>Central vs Decentralized</h2></div></div>
          {!chartData && <div className="muted text-mono">Run a comparison to see head-to-head metrics.</div>}
          {chartData && (
            <div data-testid="experiments-compare-chart">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData}>
                <CartesianGrid stroke="#232a34" strokeDasharray="3 3" />
                <XAxis dataKey="metric" stroke="#8c95a1" tick={{ fontSize: 10 }} />
                <YAxis stroke="#8c95a1" tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ background: "#141920", border: "1px solid #303844", color: "#eef1f5" }} />
                <Legend />
                <Bar dataKey="centralized" fill="#6aa2ff" name="Centralized" />
                <Bar dataKey="decentralized" fill="#35c8d1" name="Decentralized" />
              </BarChart>
            </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      <div className="panel">
        <div className="panel-head"><div><span className="panel-kicker">RESULTS</span><h2>{results.length} runs</h2></div></div>
        <div style={{ overflowX: "auto" }}>
          <table className="table" data-testid="experiments-results-table">
            <thead>
              <tr>
                <th>SCENARIO</th><th>MODE</th><th>AGENTS</th>
                {COLS.map(c => <th key={c.key}>{c.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={r.__key || r.id || `exp-${i}`} data-testid={`experiments-row-${i}`}>
                  <td className="mono">{r.scenario_label || r.scenario}</td>
                  <td><span className={`pill ${r.mode === "centralized" ? "blue" : "cyan"}`}><i />{r.mode}</span></td>
                  <td>{r.agent_count}</td>
                  {COLS.map(c => <td key={c.key} className="mono">{r[c.key] ?? "—"}</td>)}
                </tr>
              ))}
              {results.length === 0 && <tr><td colSpan={11} className="muted text-mono">No results yet — run an experiment.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
