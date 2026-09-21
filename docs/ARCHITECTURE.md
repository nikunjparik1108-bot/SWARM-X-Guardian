# SWARM-X Guardian — Architecture

## Runtime topology

```text
Browser Control Room ── REST /api ── FastAPI Gateway
                                      ├─ Simulation Clock
                                      ├─ Agent Registry + local state
                                      ├─ Auction / utility allocator
                                      ├─ A* navigation adapter
                                      └─ Transport Adapter
                                          ├─ MQTT broker (production)
                                          └─ In-process mesh fallback (demo)
Pygame Field Simulator ────────────────┘
PostgreSQL (production persistence: missions, agents, tasks, events, benchmarks)
```

The prototype runs without a broker or database so a judge can launch a repeatable demo immediately. Production mode swaps the adapters without changing the dashboard contract.

## Agent state machine

`STANDBY → BIDDING → ASSIGNED → NAVIGATING → DELIVERING → CHARGING → STANDBY`

Any state can enter `DEGRADED` on communication loss, `RETURNING` on battery reserve, or `FAILED` after heartbeat timeout. A neighboring agent starts a local auction for the orphaned task; no central coordinator is required.

## Utility score

`utility = priority_weight - (distance_cost × 0.45) - (battery_cost × 0.35) - (communication_risk × 0.20)`

Tie-breaking prefers the agent with the freshest local state and the lowest projected collision risk.