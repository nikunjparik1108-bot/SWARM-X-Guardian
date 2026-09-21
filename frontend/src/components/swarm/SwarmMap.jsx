import { useMemo } from "react";
import { X, Zap, BatteryCharging } from "lucide-react";

const scaleX = (x, w) => `${(x / 1000) * 100}%`;
const scaleY = (y, h) => `${(y / 640) * 100}%`;

export function SwarmMap({ state, onSelect, showLinks = true, showTasks = true, compact = false }) {
  const world = state?.world || { w: 1000, h: 640, charge_pad: [60, 580] };
  const agents = state?.agents || [];
  const links = state?.links || [];
  const tasks = (state?.tasks || []).filter(t => t.status !== "DELIVERED");
  const obstacles = state?.obstacles || [];

  const linkLines = useMemo(() => {
    if (!showLinks) return [];
    const byId = Object.fromEntries(agents.map(a => [a.id, a]));
    return links.slice(0, 200).map((l, i) => {
      const a = byId[l.a]; const b = byId[l.b];
      if (!a || !b) return null;
      const x1 = (a.x / world.w) * 100;
      const y1 = (a.y / world.h) * 100;
      const x2 = (b.x / world.w) * 100;
      const y2 = (b.y / world.h) * 100;
      const dx = x2 - x1; const dy = y2 - y1;
      const length = Math.sqrt(dx * dx + dy * dy);
      const angle = Math.atan2(dy, dx) * (180 / Math.PI);
      const tone = l.signal > 0.75 ? "strong" : l.signal > 0.4 ? "" : "weak";
      return (
        <div
          key={i}
          className={`map-link ${tone}`}
          style={{ left: `${x1}%`, top: `${y1}%`, width: `${length}%`, transform: `rotate(${angle}deg)` }}
        />
      );
    });
  }, [links, agents, world.w, world.h, showLinks]);

  return (
    <div className={`swarm-map ${compact ? "compact" : ""}`} data-testid="swarm-map">
      <div className="grid-bg" />
      {linkLines}
      {obstacles.filter(o => o.active).map(o => (
        <div
          key={o.id}
          className="map-obstacle"
          style={{ left: scaleX(o.x, world.w), top: scaleY(o.y, world.h), width: `${(o.w / world.w) * 100}%`, height: `${(o.h / world.h) * 100}%` }}
          data-testid={`obstacle-${o.id}`}
        >
          {o.label || "OBSTACLE"}
        </div>
      ))}
      {showTasks && tasks.slice(0, 20).map(t => (
        <div key={`p-${t.id}`}>
          <div className="map-task pickup" style={{ left: scaleX(t.pickup[0], world.w), top: scaleY(t.pickup[1], world.h) }} data-testid={`task-pickup-${t.id}`}>
            <span className="dot" /> {t.id}
          </div>
          <div className="map-task dropoff" style={{ left: scaleX(t.dropoff[0], world.w), top: scaleY(t.dropoff[1], world.h) }} data-testid={`task-dropoff-${t.id}`}>
            <span className="dot" /> ⬇
          </div>
        </div>
      ))}
      <div className="map-charge" style={{ left: scaleX(world.charge_pad[0], world.w), top: scaleY(world.charge_pad[1], world.h) }}>
        <BatteryCharging size={12} />
      </div>
      {agents.map((a, i) => (
        <button
          key={a.id}
          className={`map-agent ${a.status.toLowerCase()}`}
          style={{ left: scaleX(a.x, world.w), top: scaleY(a.y, world.h) }}
          onClick={() => onSelect?.(a)}
          title={`${a.id} · ${a.status}`}
          data-testid={`agent-${a.id}`}
          aria-label={`Agent ${a.id} state ${a.status}`}
        >
          {a.status === "FAILED" ? <X size={10} /> : (i + 1)}
        </button>
      ))}
      <div className="map-legend" data-testid="map-legend">
        <span><i style={{ background: "var(--accent)" }} />Active</span>
        <span><i style={{ background: "var(--amber)" }} />Returning</span>
        <span><i style={{ background: "var(--blue)" }} />Degraded</span>
        <span><i style={{ background: "var(--red)" }} />Failed</span>
      </div>
    </div>
  );
}
