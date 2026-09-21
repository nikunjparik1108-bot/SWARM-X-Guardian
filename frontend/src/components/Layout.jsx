import { NavLink, useLocation } from "react-router-dom";
import { useState } from "react";
import { Activity, Boxes, Cpu, FolderOpen, GitBranch, Layers, LayoutDashboard, Menu, Network, PlayCircle, Radio, ScrollText, Settings, ShieldCheck, TestTube2 } from "lucide-react";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, testId: "nav-overview", exact: true },
  { to: "/swarm", label: "Swarm", icon: Radio, testId: "nav-swarm" },
  { to: "/missions", label: "Missions", icon: Boxes, testId: "nav-missions" },
  { to: "/simulation", label: "Simulation", icon: Cpu, testId: "nav-simulation" },
  { to: "/experiments", label: "Experiments", icon: TestTube2, testId: "nav-experiments" },
  { to: "/network", label: "Network", icon: Network, testId: "nav-network" },
  { to: "/architecture", label: "Architecture", icon: Layers, testId: "nav-architecture" },
  { to: "/events", label: "Event Log", icon: ScrollText, testId: "nav-events" },
  { to: "/judge", label: "Judge Mode", icon: PlayCircle, testId: "nav-judge" },
  { to: "/files", label: "Files", icon: FolderOpen, testId: "nav-files" },
  { to: "/settings", label: "Settings", icon: Settings, testId: "nav-settings" },
];

export default function Layout({ children, state, error }) {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  const running = state?.running;
  const mode = state?.mode;
  const scenario = state?.scenario_label || state?.scenario || "—";
  const metrics = state?.metrics;

  return (
    <div className="app-shell" data-testid="app-shell">
      <header className="app-topbar" data-testid="app-topbar">
        <div className="brand">
          <div className="brand-mark"><ShieldCheck size={18} /></div>
          <div className="brand-name">
            <b>SWARM-X</b>
            <span>GUARDIAN · OPERATIONS CONSOLE</span>
          </div>
        </div>
        <div className="topbar-meta">
          <span className="pill cyan" data-testid="topbar-mode-pill"><i />{(mode || "…").toUpperCase()}</span>
          <span className="divider" />
          <span className="m-hide" data-testid="topbar-scenario">SCENARIO / {scenario.toUpperCase()}</span>
          <span className="divider m-hide" />
          <span className="m-hide" data-testid="topbar-tick">TICK · {state?.tick ?? "—"}</span>
          <span className="divider" />
          <span className={`pill ${running ? "green" : "amber"}`} data-testid="topbar-run-state">
            <i />{running ? "LIVE" : "PAUSED"}
          </span>
          <button className="btn ghost mobile-toggle" onClick={() => setOpen(!open)} aria-label="Toggle navigation" data-testid="mobile-nav-toggle">
            <Menu size={16} />
          </button>
        </div>
      </header>
      <aside className={`app-sidebar ${open ? "open" : ""}`} data-testid="app-sidebar">
        <div className="sidebar-label">CONTROL PLANE</div>
        {NAV.map((n) => {
          const Icon = n.icon;
          const active = n.exact ? location.pathname === n.to : location.pathname.startsWith(n.to);
          return (
            <NavLink
              key={n.to}
              to={n.to}
              onClick={() => setOpen(false)}
              className={`nav-item ${active ? "active" : ""}`}
              data-testid={n.testId}
            >
              <Icon size={16} />
              <span>{n.label}</span>
              {n.to === "/swarm" && metrics && <span className="count">{metrics.active_agents}</span>}
              {n.to === "/missions" && metrics && <span className="count">{metrics.pending_tasks}</span>}
              {n.to === "/events" && state && <span className="count">{state.events?.length ?? 0}</span>}
            </NavLink>
          );
        })}
        <div className="sidebar-footer">
          <div>SIMULATION · <b>{scenario}</b></div>
          <div>NETWORK · <b>{state?.network_state || "—"}</b></div>
          <div>BUILD · <b>1.0.0</b></div>
        </div>
      </aside>
      <main className="app-main" data-testid="app-main">{children}</main>
      {error && <div className="toast" data-testid="global-error-toast">{error}</div>}
    </div>
  );
}
