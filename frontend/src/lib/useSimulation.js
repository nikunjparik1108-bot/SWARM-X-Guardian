import { useEffect, useRef, useState, useCallback } from "react";
import { endpoints } from "./api";

// Central hook polled at 1Hz. Every consumer reads from this single source
// of truth — no local duplicated simulation state.
export function useSimulation(interval = 900) {
  const [state, setState] = useState(null);
  const [error, setError] = useState("");
  const alive = useRef(true);

  const load = useCallback(async () => {
    try {
      const snap = await endpoints.simulation();
      if (alive.current) { setState(snap); setError(""); }
    } catch (e) {
      if (alive.current) setError("Simulation API unavailable");
    }
  }, []);

  useEffect(() => {
    alive.current = true;
    load();
    const timer = setInterval(load, interval);
    return () => { alive.current = false; clearInterval(timer); };
  }, [load, interval]);

  // Optimistic update helper: pass a fetch that returns a new snapshot.
  const command = useCallback(async (fetcher) => {
    try {
      const snap = await fetcher();
      if (snap && snap.agents) setState(snap);
      else await load();
    } catch (e) {
      setError("Command failed");
    }
  }, [load]);

  return { state, error, command, refresh: load };
}
