# API Design

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/simulation` | Current tick, agents, tasks, events, obstacles, metrics |
| POST | `/api/simulation/toggle` | Pause/resume simulation clock |
| POST | `/api/simulation/reset` | Load normal, failure, comms, obstacle, battery, 50 or 100-agent scenario |
| POST | `/api/simulation/agents/{id}/fail` | Inject a heartbeat failure |
| POST | `/api/tasks` | Broadcast a task into the local auction |
| GET | `/api/benchmarks` | Centralized vs decentralized benchmark series |
| GET | `/api/health` | Service and transport health |

## Task payload

```json
{"pickup_x":120,"pickup_y":120,"dropoff_x":820,"dropoff_y":480,"priority":"HIGH"}
```