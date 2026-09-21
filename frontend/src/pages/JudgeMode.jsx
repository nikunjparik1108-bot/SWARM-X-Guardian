import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Play, RotateCcw } from "lucide-react";
import { SwarmMap } from "../components/swarm/SwarmMap";
import EventStream from "../components/swarm/EventStream";
import { endpoints } from "../lib/api";

// Judge Mode drives the *real* simulation through a scripted sequence.
// Each step waits for an observable condition on the world state.

const STEP_CONDITIONS = {
  1: (s) => s.metrics.active_agents >= 5,
  2: (s) => s.tasks.some(t => t.priority === "HIGH"),
  3: (s) => s.tasks.some(t => t.status === "AUCTIONING"),
  4: (s) => s.tasks.some(t => t.priority === "HIGH" && t.status !== "AUCTIONING"),
  5: (s) => s.tasks.some(t => t.priority === "HIGH" && (t.status === "IN_TRANSIT" || t.status === "ASSIGNED")),
  6: (s) => s.metrics.failed_agents >= 1,
  7: (s) => s.events.some(e => e.kind === "FAILURE"),
  8: (s) => s.tasks.some(t => t.status === "INTERRUPTED") || s.events.some(e => e.message.includes("released")),
  9: (s) => s.events.some(e => e.kind === "AUCTION" && s.events.some(x => x.kind === "FAILURE")),
  10: (s) => s.events.some(e => e.kind === "RECOVERY" && e.message.includes("accepted")),
  11: (s) => s.events.filter(e => e.kind === "RECOVERY").length >= 1,
  12: (s) => s.metrics.recovered_tasks >= 1,
  13: (s) => s.metrics.completed_tasks >= 1,
};

export default function JudgeMode({ state, command }) {
  const [steps, setSteps] = useState([]);
  const [current, setCurrent] = useState(0);
  const [running, setRunning] = useState(false);
  const [complete, setComplete] = useState(false);
  const stepRef = useRef(0);

  useEffect(() => { endpoints.judgeScript().then(d => setSteps(d.steps)); }, []);

  useEffect(() => {
    if (!running || !state || complete) return;
    const idx = stepRef.current;
    if (idx >= steps.length) {
      setComplete(true); setRunning(false); return;
    }
    const step = steps[idx];
    const check = STEP_CONDITIONS[step.id];
    if (check && check(state)) {
      stepRef.current = idx + 1;
      setCurrent(stepRef.current);
    }
  }, [state, steps, running, complete]);

  const start = async () => {
    stepRef.current = 0; setCurrent(0); setComplete(false);
    await command(endpoints.judgeStart);
    setRunning(true);
  };

  const reset = async () => {
    setRunning(false); setComplete(false);
    stepRef.current = 0; setCurrent(0);
    await command(() => endpoints.reset({ scenario: "normal", agent_count: 10, mode: "decentralized" }));
  };

  const active = steps[Math.min(current, steps.length - 1)];

  return (
    <>
      <div className="page-header">
        <div>
          <div className="eyebrow">/ JUDGE MODE · GUIDED DEMONSTRATION</div>
          <h1>Decentralized recovery, in 60 seconds.</h1>
          <p>Each step is triggered by an observable transition in the running simulation — not an animation.</p>
        </div>
        <div className="page-actions">
          <button className="btn ghost" onClick={reset} data-testid="judge-reset-button"><RotateCcw size={14} /> Reset</button>
          <button className="btn primary" onClick={start} disabled={running} data-testid="judge-start-button"><Play size={14} /> Start demo</button>
        </div>
      </div>

      <div className="split-2">
        <div className="panel judge-stage">
          <div className="panel-head">
            <div>
              <span className="panel-kicker">LIVE STAGE</span>
              <h2>Mission topology</h2>
            </div>
            {complete && <span className="pill green" data-testid="judge-complete"><i /><CheckCircle2 size={12} /> DEMONSTRATED</span>}
          </div>
          <SwarmMap state={state} />
          <div className="judge-timeline" data-testid="judge-timeline">
            {steps.map((s, i) => (
              <div key={s.id} className={`judge-step ${i < current ? "done" : i === current ? "current" : ""}`} data-testid={`judge-step-${s.id}`}>{s.id}</div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <span className="panel-kicker">STEP {active?.id ?? "—"} / {steps.length}</span>
              <h2>{active?.label || "Awaiting start"}</h2>
            </div>
          </div>
          <p className="muted" data-testid="judge-step-description">{active?.description || "Click Start demo to begin the recovery narrative."}</p>
          {complete && <p style={{ marginTop: 12, color: "var(--green)" }} className="text-mono" data-testid="judge-complete-banner">DECENTRALIZED MISSION RECOVERY DEMONSTRATED</p>}
          <div style={{ marginTop: 20 }}>
            <span className="panel-kicker">EVENT STREAM</span>
            <EventStream events={state.events} max={12} testId="judge-events" />
          </div>
        </div>
      </div>
    </>
  );
}
