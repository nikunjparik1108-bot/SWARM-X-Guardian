export default function Settings({ state }) {
  return (
    <div data-testid="settings-page">
      <div className="page-header">
        <div>
          <div className="eyebrow">/ SETTINGS · PROJECT INFO</div>
          <h1>About this simulation.</h1>
          <p>Documentation, credits, and limitations of the current prototype.</p>
        </div>
      </div>
      <div className="split-2">
        <div className="panel">
          <span className="panel-kicker">PROJECT</span>
          <h2>SWARM-X Guardian</h2>
          <p className="muted">A software prototype of decentralized multi-agent coordination for autonomous logistics. Each agent maintains local state and coordinates through a simulated peer-to-peer mesh; there is no central controller in the default (decentralized) mode.</p>
          <div className="inspect-row"><span>Backend</span><b>FastAPI · Python</b></div>
          <div className="inspect-row"><span>Frontend</span><b>React · Recharts</b></div>
          <div className="inspect-row"><span>Coordination</span><b>Utility auction · local scoring</b></div>
          <div className="inspect-row"><span>Persistence</span><b>In-memory (deterministic)</b></div>
          <div className="inspect-row"><span>Version</span><b>1.0.0</b></div>
        </div>
        <div className="panel">
          <span className="panel-kicker">LIMITATIONS</span>
          <h2>What this is not</h2>
          <ul className="muted" style={{ paddingLeft: 18 }}>
            <li>Not a certified aviation control system. This is a software prototype.</li>
            <li>The peer-to-peer mesh is simulated in-process; no real MQTT / radio hardware.</li>
            <li>Safety separation is enforced through a simplified minimum-distance constraint.</li>
            <li>Metrics are calculated over the current in-memory run; they do not persist across restarts.</li>
          </ul>
          <div style={{ marginTop: 14 }}>
            <span className="panel-kicker">CURRENT SNAPSHOT</span>
            <div className="inspect-row"><span>Mode</span><b data-testid="settings-mode">{state.mode}</b></div>
            <div className="inspect-row"><span>Scenario</span><b>{state.scenario}</b></div>
            <div className="inspect-row"><span>Network</span><b>{state.network_state}</b></div>
            <div className="inspect-row"><span>Sim time</span><b>{state.sim_time} s</b></div>
          </div>
        </div>
      </div>
    </div>
  );
}
