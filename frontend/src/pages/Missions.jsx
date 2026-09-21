import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import { endpoints } from "../lib/api";

export default function Missions({ state, command }) {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ pickup_x: 180, pickup_y: 480, dropoff_x: 820, dropoff_y: 160, priority: "MEDIUM", payload_weight: 1.4 });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await endpoints.createTask(form);
      if (res.state) await command(() => Promise.resolve(res.state));
    } finally {
      setBusy(false);
      setShowForm(false);
    }
  };

  const pending = state.tasks.filter(t => t.status !== "DELIVERED");
  const completed = state.completed_tasks || [];

  return (
    <>
      <div className="page-header">
        <div>
          <div className="eyebrow">/ MISSIONS · DELIVERY QUEUE</div>
          <h1>Broadcast tasks. Watch the swarm bid.</h1>
          <p>Every new task is announced to peers. Eligible agents score it locally against battery, distance, payload, workload, ETA and priority — highest utility wins.</p>
        </div>
        <div className="page-actions">
          <button className="btn primary" onClick={() => setShowForm(true)} data-testid="missions-new-task-button">
            <Plus size={14} /> New task
          </button>
        </div>
      </div>

      <div className="split-2">
        <div className="panel">
          <div className="panel-head">
            <div>
              <span className="panel-kicker">ACTIVE QUEUE</span>
              <h2>{pending.length} in flight</h2>
            </div>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="table" data-testid="missions-pending-table">
              <thead><tr><th>ID</th><th>STATUS</th><th>PRIO</th><th>KG</th><th>AGENT</th><th>REASSIGN</th></tr></thead>
              <tbody>
                {pending.map(t => (
                  <tr key={t.id} data-testid={`missions-pending-${t.id}`}>
                    <td className="mono">{t.id}</td>
                    <td><span className={`pill ${t.status === "INTERRUPTED" ? "red" : t.status === "AUCTIONING" ? "blue" : "cyan"}`}><i />{t.status}</span></td>
                    <td>{t.priority}</td>
                    <td>{t.payload_weight}</td>
                    <td className="mono">{t.assigned_agent || "—"}</td>
                    <td>{t.reassignments}</td>
                  </tr>
                ))}
                {pending.length === 0 && <tr><td colSpan={6} className="muted text-mono">No pending missions — inject one.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
        <div className="panel">
          <div className="panel-head">
            <div>
              <span className="panel-kicker">COMPLETED</span>
              <h2>{completed.length} delivered</h2>
            </div>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="table" data-testid="missions-completed-table">
              <thead><tr><th>ID</th><th>AGENT</th><th>DELIVERY (s)</th><th></th></tr></thead>
              <tbody>
                {completed.slice(-10).reverse().map(t => (
                  <tr key={t.id} data-testid={`missions-completed-${t.id}`}>
                    <td className="mono">{t.id}</td>
                    <td className="mono">{t.assigned_agent || "—"}</td>
                    <td>{(t.delivered_at != null && t.created_at != null) ? (t.delivered_at - t.created_at).toFixed(1) : "—"}</td>
                    <td>
                      <Link to={`/files?category=delivery&ref=${t.id}`} className="btn ghost tiny" data-testid={`missions-attach-${t.id}`}>
                        Attach proof
                      </Link>
                    </td>
                  </tr>
                ))}
                {completed.length === 0 && <tr><td colSpan={4} className="muted text-mono">No completions yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {showForm && (
        <div className="inspector-overlay" onClick={() => setShowForm(false)} data-testid="missions-form-overlay">
          <aside className="inspector-panel" onClick={e => e.stopPropagation()}>
            <span className="panel-kicker">MISSION QUEUE</span>
            <h2>Broadcast a delivery</h2>
            <form onSubmit={submit} data-testid="missions-new-task-form">
              <div className="field">
                <label>Priority</label>
                <select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })} data-testid="task-priority">
                  <option>LOW</option><option>MEDIUM</option><option>HIGH</option>
                </select>
              </div>
              <div className="form-grid">
                <div className="field"><label>Pickup X</label><input type="number" min="0" max="1000" value={form.pickup_x} onChange={e => setForm({ ...form, pickup_x: Number(e.target.value) })} data-testid="task-pickup-x" /></div>
                <div className="field"><label>Pickup Y</label><input type="number" min="0" max="640" value={form.pickup_y} onChange={e => setForm({ ...form, pickup_y: Number(e.target.value) })} data-testid="task-pickup-y" /></div>
                <div className="field"><label>Dropoff X</label><input type="number" min="0" max="1000" value={form.dropoff_x} onChange={e => setForm({ ...form, dropoff_x: Number(e.target.value) })} data-testid="task-dropoff-x" /></div>
                <div className="field"><label>Dropoff Y</label><input type="number" min="0" max="640" value={form.dropoff_y} onChange={e => setForm({ ...form, dropoff_y: Number(e.target.value) })} data-testid="task-dropoff-y" /></div>
              </div>
              <div className="field"><label>Payload (kg)</label><input type="number" step="0.1" min="0.1" max="10" value={form.payload_weight} onChange={e => setForm({ ...form, payload_weight: Number(e.target.value) })} data-testid="task-weight" /></div>
              <div className="hstack" style={{ justifyContent: "flex-end", marginTop: 12 }}>
                <button type="button" className="btn ghost" onClick={() => setShowForm(false)} data-testid="task-cancel-button">Cancel</button>
                <button type="submit" className="btn primary" disabled={busy} data-testid="task-submit-button">
                  <Plus size={14} /> Broadcast
                </button>
              </div>
            </form>
          </aside>
        </div>
      )}
    </>
  );
}
