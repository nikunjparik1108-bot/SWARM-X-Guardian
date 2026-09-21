# MQTT Topics

| Topic | Direction | Payload |
|---|---|---|
| `swarm/guardian/agents/{id}/heartbeat` | agent → peers | position, battery, state, sequence |
| `swarm/guardian/agents/{id}/state` | agent → peers | task, velocity, neighbors |
| `swarm/guardian/tasks/announce` | peer broadcast | task, priority, deadline |
| `swarm/guardian/tasks/{id}/bid` | agent → peers | utility, ETA, risk |
| `swarm/guardian/tasks/{id}/award` | winning peer → peers | winner, lease, route |
| `swarm/guardian/recovery` | peer broadcast | failed agent, orphaned task, recovery time |
| `swarm/guardian/obstacles` | sensor → peers | obstacle geometry, confidence |

The local mesh fallback exposes the same event contract through the FastAPI snapshot. Production MQTT should use retained heartbeats, QoS 1 for task events, and a last-will message for agent failure.