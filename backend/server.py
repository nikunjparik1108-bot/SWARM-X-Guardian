"""FastAPI server for SWARM-X Guardian.

Wraps the simulation.World with a REST API used by the React operations
console. All metrics come from real simulation state — no hardcoded values.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from simulation import World, WORLD_W, WORLD_H
from simulation.mesh import NetworkState
from simulation.experiments import EXPERIMENT_SCENARIOS, run_comparison, run_experiment

app = FastAPI(title="SWARM-X Guardian API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

world = World(agent_count=12, mode="decentralized")


# -----------------------------  Models  -----------------------------
class TaskCreate(BaseModel):
    pickup_x: float = Field(ge=0, le=WORLD_W)
    pickup_y: float = Field(ge=0, le=WORLD_H)
    dropoff_x: float = Field(ge=0, le=WORLD_W)
    dropoff_y: float = Field(ge=0, le=WORLD_H)
    priority: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH)$")
    payload_weight: float = Field(default=1.2, gt=0, le=10)


class ResetRequest(BaseModel):
    scenario: str = "normal"
    agent_count: int = Field(default=12, ge=3, le=100)
    mode: str = Field(default="decentralized", pattern="^(decentralized|centralized)$")


class NetworkRequest(BaseModel):
    state: str


class FailRequest(BaseModel):
    agent_id: str


class ExperimentRequest(BaseModel):
    scenario: str
    mode: str = Field(default="decentralized", pattern="^(decentralized|centralized)$")
    agent_count: int | None = Field(default=None, ge=3, le=100)


class ModeRequest(BaseModel):
    mode: str = Field(pattern="^(decentralized|centralized)$")


# -----------------------------  Lifecycle  -----------------------------
@app.on_event("startup")
async def _start_loop():
    async def _tick():
        while True:
            world.step()
            await asyncio.sleep(0.4)
    asyncio.create_task(_tick())


# -----------------------------  Meta  -----------------------------
@app.get("/api/")
async def root():
    return {"service": "SWARM-X Guardian", "version": "1.0.0",
            "mode": world.mode, "scenario": world.scenario}


@app.get("/api/health")
async def health():
    return {"status": "ok", "running": world.running,
            "agents": len(world.agents), "tick": world.tick}


# -----------------------------  Simulation state  -----------------------------
@app.get("/api/simulation")
async def get_simulation():
    return world.snapshot()


@app.post("/api/simulation/toggle")
async def toggle_simulation():
    world.running = not world.running
    world.log("SYSTEM", f"Simulation {'resumed' if world.running else 'paused'}")
    return world.snapshot()


@app.post("/api/simulation/reset")
async def reset_simulation(req: ResetRequest):
    world.reset(agent_count=req.agent_count, mode=req.mode, scenario=req.scenario)
    return world.snapshot()


@app.post("/api/simulation/mode")
async def set_mode(req: ModeRequest):
    world.mode = req.mode
    world.log("SYSTEM", f"Coordination mode → {req.mode}")
    return world.snapshot()


@app.post("/api/simulation/network")
async def set_network(req: NetworkRequest):
    if req.state not in {NetworkState.NORMAL, NetworkState.DEGRADED,
                          NetworkState.HIGH_PACKET_LOSS,
                          NetworkState.PARTIAL_PARTITION,
                          NetworkState.RECOVERED}:
        raise HTTPException(400, "Unknown network state")
    world.set_network_state(req.state)
    return world.snapshot()


# -----------------------------  Agents  -----------------------------
@app.get("/api/agents")
async def list_agents():
    return {"agents": [a.to_dict() for a in world.agents]}


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = next((a for a in world.agents if a.id == agent_id), None)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent.to_dict()


@app.post("/api/agents/{agent_id}/fail")
async def fail_agent(agent_id: str):
    agent = world.fail_agent(agent_id, reason="manual_injection")
    if not agent:
        raise HTTPException(404, "Agent not found or already failed")
    return world.snapshot()


# -----------------------------  Tasks  -----------------------------
@app.get("/api/tasks")
async def list_tasks():
    return {
        "tasks": [t.to_dict() for t in world.tasks],
        "completed": [t.to_dict() for t in world.completed_tasks[-30:]],
    }


@app.post("/api/tasks")
async def create_task(body: TaskCreate):
    task = world.spawn_task(
        pickup=(body.pickup_x, body.pickup_y),
        dropoff=(body.dropoff_x, body.dropoff_y),
        priority=body.priority,
        payload_weight=body.payload_weight,
    )
    return {"task": task.to_dict(), "state": world.snapshot()}


# -----------------------------  Events / metrics  -----------------------------
@app.get("/api/events")
async def events(limit: int = 100):
    return {"events": list(world.events)[:max(1, min(limit, 400))]}


@app.get("/api/metrics")
async def metrics():
    return world._metrics()


# -----------------------------  Experiments  -----------------------------
@app.get("/api/experiments/scenarios")
async def experiment_scenarios() -> dict[str, Any]:
    return {
        "scenarios": [
            {"id": key, **{k: v for k, v in cfg.items()
                            if k in {"label", "description", "agent_count", "duration_ticks"}}}
            for key, cfg in EXPERIMENT_SCENARIOS.items()
        ]
    }


@app.post("/api/experiments/run")
async def experiments_run(req: ExperimentRequest):
    try:
        # Run in a thread so we don't block the event loop
        result = await asyncio.to_thread(
            run_experiment, req.scenario, req.mode, req.agent_count,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return result


@app.post("/api/experiments/compare")
async def experiments_compare(req: ExperimentRequest):
    try:
        result = await asyncio.to_thread(run_comparison, req.scenario)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return result


# -----------------------------  Judge mode  -----------------------------
# The Judge Mode "script" is executed *live* on the running simulation so
# every step is a real state transition, not a rehearsed animation.

JUDGE_SCRIPT = [
    {"id": 1, "label": "Normal swarm operation",
     "description": "Agents coordinate locally; tasks flow through the mesh."},
    {"id": 2, "label": "Task announcement",
     "description": "A new high-priority delivery is broadcast to peers."},
    {"id": 3, "label": "Local evaluation",
     "description": "Every eligible agent scores the task independently."},
    {"id": 4, "label": "Task accepted",
     "description": "Highest-utility agent wins the auction and locks the task."},
    {"id": 5, "label": "Route execution",
     "description": "Agent picks up payload and begins delivery run."},
    {"id": 6, "label": "Agent failure injected",
     "description": "Assigned agent is failed mid-mission."},
    {"id": 7, "label": "Neighbor detection",
     "description": "Peers observe heartbeat timeout and flag the failure."},
    {"id": 8, "label": "Task released",
     "description": "Interrupted delivery becomes available for re-auction."},
    {"id": 9, "label": "Peer bidding",
     "description": "Local peers evaluate the released task."},
    {"id": 10, "label": "Replacement accepted",
     "description": "New agent commits to the delivery."},
    {"id": 11, "label": "Route recalculated",
     "description": "Replacement plans a fresh route from its position."},
    {"id": 12, "label": "Mission continues",
     "description": "Delivery flow resumes without central intervention."},
    {"id": 13, "label": "Delivery completed",
     "description": "Payload delivered; recovery metrics recorded."},
]


@app.get("/api/judge/script")
async def judge_script():
    return {"steps": JUDGE_SCRIPT}


@app.post("/api/judge/start")
async def judge_start():
    """Reset the world into a controlled judge-mode initial state."""
    world.reset(agent_count=10, mode="decentralized", scenario="agent_failure")
    # Seed a distinctive HIGH-priority task the demo highlights.
    world.spawn_task(pickup=(180, 480), dropoff=(820, 160), priority="HIGH",
                      payload_weight=1.6)
    world.log("SYSTEM", "Judge mode initialized — decentralized recovery demo")
    return world.snapshot()
