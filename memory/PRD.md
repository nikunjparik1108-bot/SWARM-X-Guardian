# SWARM-X Guardian — Product Requirements Document

## Original Problem Statement
Decentralized multi-agent coordination for autonomous logistics. Traditional autonomous logistics systems can depend heavily on a central controller. If that controller or communication path fails, fleet operations may be disrupted. The prototype demonstrates a decentralized multi-agent architecture in which individual autonomous agents maintain their own local state, communicate with nearby agents, discover neighboring agents, evaluate tasks locally, coordinate task allocation, dynamically reassign work, adapt to individual-agent failures, respond to degraded communication, avoid unsafe conflicts, and continue the mission without requiring a single central decision-maker.

## Architecture
- **Backend** (FastAPI, Python)
  - `simulation/agent.py` — Agent state machine (IDLE→SEARCHING→EVALUATING→NEGOTIATING→ASSIGNED→EN_ROUTE→DELIVERING→RETURNING→DEGRADED→FAILED→RECOVERING)
  - `simulation/task.py` — Task lifecycle
  - `simulation/allocator.py` — Utility-based auction (weights: distance, battery, payload, workload, ETA, priority)
  - `simulation/mesh.py` — Peer mesh (distance-based neighbors, latency/loss/signal, heartbeat timeout detection, partition scenarios)
  - `simulation/world.py` — Simulation controller + real computed metrics
  - `simulation/experiments.py` — Deterministic scenario runners for measured results
  - `server.py` — REST API (`/api/simulation`, `/api/tasks`, `/api/agents/{id}/fail`, `/api/experiments/...`, `/api/judge/...`)
- **Frontend** (React 19 + React Router + Recharts)
  - Layout with sidebar + topbar; pages: Overview, Swarm, Missions, Simulation, Experiments, Network, Architecture, Event Log, Judge Mode, Settings
  - Shared components: `SwarmMap`, `AgentInspector`, `EventStream`

## Personas
- **KPIT Sparkle judge** — needs a compact 60-second guided demo (Judge Mode)
- **Robotics engineer** — inspects Architecture, Experiments, Network layers
- **Logistics reviewer** — inspects Missions + Fleet health + measured recovery metrics
- **Undergraduate innovator** — presents the whole system end-to-end

## What's implemented (2026-02)
- Full decentralized simulation with real agent state machine, transparent scoring, peer mesh, heartbeat monitoring, failure recovery
- Multi-page operations console with 10 routes, all live-linked to the same simulation snapshot (single source of truth)
- Real Experiments engine with deterministic seeded runs, Centralized vs Decentralized comparison, CSV export
- Judge Mode driven by real state transitions (not animation)
- Architecture Explorer with 6 layers
- Live Event Log with filtering
- Responsive layout (desktop / tablet / mobile 390px)

## Backlog
- **P1**: Persistent history so multiple experiment runs survive backend restarts
- **P1**: Multi-tenant per-user simulation instance
- **P2**: A* obstacle-aware pathfinding (currently straight-line with safety separation)
- **P2**: WebSocket push instead of polling
- **P2**: Export PPT / research paper generator

## Test Coverage
- Backend regression: 14/14 pytest cases pass (see `/app/backend/tests/backend_test.py`)
- Frontend flows: all 22 flows in latest iteration report pass with 0 console errors
- Responsive verified at 1920×800 and 390×844
