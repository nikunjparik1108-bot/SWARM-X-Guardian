import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { endpoints } from "@/lib/api";
import { useSimulation } from "@/lib/useSimulation";
import Layout from "@/components/Layout";
import CopilotPanel from "@/components/copilot/CopilotPanel";
import Overview from "@/pages/Overview";
import Swarm from "@/pages/Swarm";
import Missions from "@/pages/Missions";
import SimulationPage from "@/pages/Simulation";
import Experiments from "@/pages/Experiments";
import NetworkPage from "@/pages/Network";
import ArchitecturePage from "@/pages/Architecture";
import EventLogPage from "@/pages/EventLog";
import JudgeMode from "@/pages/JudgeMode";
import FilesPage from "@/pages/Files";
import Settings from "@/pages/Settings";
import "@/App.css";

function Boot() {
  return (
    <div className="boot-screen" data-testid="boot-screen">
      <div className="pulse" />
      <ShieldCheck size={26} />
      <div className="text-mono muted">Connecting to Guardian mesh…</div>
    </div>
  );
}

export default function App() {
  const { state, command, error } = useSimulation(900);
  const [integrations, setIntegrations] = useState({ storage_enabled: false, copilot_enabled: false });

  useEffect(() => {
    let alive = true;
    endpoints.integrationsStatus()
      .then((r) => { if (alive) setIntegrations(r); })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  if (!state) return <Boot />;
  return (
    <BrowserRouter>
      <Layout state={state} error={error} integrations={integrations}>
        <Routes>
          <Route path="/" element={<Overview state={state} command={command} error={error} />} />
          <Route path="/swarm" element={<Swarm state={state} command={command} />} />
          <Route path="/missions" element={<Missions state={state} command={command} />} />
          <Route path="/simulation" element={<SimulationPage state={state} command={command} />} />
          <Route path="/experiments" element={<Experiments />} />
          <Route path="/network" element={<NetworkPage state={state} command={command} />} />
          <Route path="/architecture" element={<ArchitecturePage />} />
          <Route path="/events" element={<EventLogPage state={state} />} />
          <Route path="/judge" element={<JudgeMode state={state} command={command} />} />
          <Route path="/files" element={<FilesPage state={state} integrations={integrations} />} />
          <Route path="/settings" element={<Settings state={state} integrations={integrations} />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </Layout>
      <CopilotPanel enabled={integrations.copilot_enabled} />
    </BrowserRouter>
  );
}
