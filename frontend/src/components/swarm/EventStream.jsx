import { AlertCircle, ShieldCheck, Radio, Truck, Zap, PlaneTakeoff, WifiOff, RefreshCw } from "lucide-react";

const ICON_BY_KIND = {
  RECOVERY: ShieldCheck,
  FAILURE: AlertCircle,
  AUCTION: Radio,
  TASK: Truck,
  DELIVERY: Truck,
  NAV: PlaneTakeoff,
  NETWORK: WifiOff,
  SYSTEM: RefreshCw,
  SAFETY: AlertCircle,
  BATTERY: Zap,
};

export default function EventStream({ events, testId = "event-stream", max = 60 }) {
  const list = (events || []).slice(0, max);
  if (!list.length) return <div className="muted text-mono">No events yet — waiting for swarm activity.</div>;
  return (
    <div className="event-list" data-testid={testId}>
      {list.map(e => {
        const Icon = ICON_BY_KIND[e.kind] || Radio;
        return (
          <div key={e.id} className={`event-item ${e.kind.toLowerCase()}`} data-testid={`event-${e.id}`}>
            <span className="kind"><Icon size={11} style={{ marginRight: 4 }} />{e.kind}</span>
            <span className="msg">{e.message}</span>
            <span className="ts">{e.time}</span>
          </div>
        );
      })}
    </div>
  );
}
