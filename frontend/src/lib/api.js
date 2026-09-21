import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API, timeout: 15000 });

export const endpoints = {
  simulation: () => api.get("/simulation").then(r => r.data),
  toggle: () => api.post("/simulation/toggle").then(r => r.data),
  reset: (body) => api.post("/simulation/reset", body).then(r => r.data),
  mode: (mode) => api.post("/simulation/mode", { mode }).then(r => r.data),
  network: (state) => api.post("/simulation/network", { state }).then(r => r.data),
  failAgent: (id) => api.post(`/agents/${id}/fail`).then(r => r.data),
  createTask: (body) => api.post("/tasks", body).then(r => r.data),
  events: (limit = 120) => api.get(`/events?limit=${limit}`).then(r => r.data),
  metrics: () => api.get("/metrics").then(r => r.data),
  experimentScenarios: () => api.get("/experiments/scenarios").then(r => r.data),
  runExperiment: (body) => api.post("/experiments/run", body).then(r => r.data),
  compareExperiment: (body) => api.post("/experiments/compare", body).then(r => r.data),
  judgeScript: () => api.get("/judge/script").then(r => r.data),
  judgeStart: () => api.post("/judge/start").then(r => r.data),
};

export const NETWORK_STATES = ["NORMAL", "DEGRADED", "HIGH_PACKET_LOSS", "PARTIAL_PARTITION", "RECOVERED"];

export const AGENT_STATUS_TONE = {
  IDLE: "muted", SEARCHING: "muted",
  EVALUATING: "cyan", NEGOTIATING: "cyan",
  ASSIGNED: "cyan", EN_ROUTE: "cyan", DELIVERING: "cyan",
  RETURNING: "amber", RECOVERING: "amber", DEGRADED: "blue",
  FAILED: "red",
};

export const TASK_STATUS_TONE = {
  PENDING: "muted", AUCTIONING: "blue", ASSIGNED: "cyan",
  IN_TRANSIT: "cyan", DELIVERING: "cyan", DELIVERED: "green",
  INTERRUPTED: "red",
};
