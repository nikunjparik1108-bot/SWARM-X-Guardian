# SWARM-X Guardian
Decentralized multi-agent coordination for autonomous logistics (software prototype).

## What it demonstrates
- **Local agent decisions** — each agent scores tasks via a transparent utility function
- **Peer-to-peer mesh** — distance-based neighbor discovery, heartbeat monitoring, packet loss / latency simulation
- **Auction-based task allocation** — highest-utility bidder wins
- **Failure recovery** — killed agents release their tasks; peers detect timeouts and re-auction
- **Network degradation** — normal / degraded / high-packet-loss / partial-partition / recovered profiles
- **Experiments** — deterministic scenario runs producing measured, comparable results
- **Judge mode** — a 60-second guided demonstration driven by real state transitions

## Stack
- Backend: FastAPI + custom simulation package (`backend/simulation/`)
- Frontend: React + React Router + Recharts
- Simulation state lives in-memory; the app is a prototype, not a certified control system.

## Local dev
Both services run under supervisor.
- Backend: `sudo supervisorctl restart backend`
- Frontend: `sudo supervisorctl restart frontend`

Environment:
- `REACT_APP_BACKEND_URL` in `frontend/.env`
- All backend routes are `/api/*`
