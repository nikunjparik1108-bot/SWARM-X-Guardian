# SWARM-X Guardian PRD

## Original problem statement
Build SWARM-X Guardian, a decentralized self-healing multi-agent coordination platform for autonomous logistics that continues mission operations through controller failure, agent failure, communication loss, dynamic obstacles, and battery depletion. The prototype must include a browser dashboard, Python/Pygame simulator, FastAPI, MQTT with local fallback, PostgreSQL target schema, measurable benchmarks, and judge-ready KPIT Sparkle materials.

## User choices and persona
- User chose both browser dashboard and Pygame simulator.
- User chose PostgreSQL as the target data store.
- User chose MQTT with an in-process fallback for demos.
- User needs live controls, manual task creation, and agent inspection.
- Primary persona: undergraduate robotics innovator presenting a resilient swarm concept to KPIT judges and logistics operators.

## Architecture decisions
- React dashboard uses the existing `REACT_APP_BACKEND_URL` and calls FastAPI REST endpoints.
- FastAPI owns a deterministic simulation clock, scenario fixtures, agent health, recovery events, and task auction events.
- Transport is adapter-shaped: the current working demo uses an in-process fallback; MQTT topics are documented for production.
- PostgreSQL schema is documented as the persistence target; the demo remains runnable without external credentials.
- Pygame is a standalone field demonstrator for offline judging.

## Core requirements
- Show active/failed agents, communications health, recovery events, mission success, task completion, and topology.
- Run normal, failure, communication loss, obstacle, battery, 50-agent, and 100-agent scenarios.
- Inject agent failures and create prioritized manual tasks.
- Inspect agent state including battery, velocity, neighbors, task, position, and status.
- Compare centralized and decentralized benchmark curves.
- Provide architecture, API, MQTT, schema, demo, research, patent, and business documentation.

## Implemented — 2026-09-21
- Tactical browser command center with responsive desktop/mobile layout.
- FastAPI simulation service with live state polling and scenario reset/toggle endpoints.
- Recovery feed with heartbeat failure, local auction, communications degradation, and battery reserve states.
- Task broadcast modal and agent inspection/failure injection flow.
- Pygame field simulator with keyboard-driven pause, reset, failure, and obstacle controls.
- Architecture, API, MQTT, PostgreSQL schema, demo script, and research/business/patent brief.
- Frontend production build and live preview smoke check passed.

## Prioritized backlog
### P0
- Add an actual local PostgreSQL service and Alembic migrations for mission history.
- Add a local MQTT broker adapter and heartbeat last-will handling.
- Persist benchmark runs and export CSV results.
### P1
- Implement grid-based A* route visualization and collision counters.
- Add benchmark page with live charts and run comparison.
- Add multi-mission playback and downloadable judge report.
### P2
- Hardware-in-the-loop adapter for drone/AGV telemetry.
- Signed task leases and Byzantine peer scoring.
- Operator roles and audit log.

## Next tasks
1. Wire PostgreSQL and MQTT adapters behind the documented contracts.
2. Add benchmark chart route and CSV export.
3. Validate Pygame and browser metrics against the same replay seed.