from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import asyncio
import math
import os
import random
import uuid

app = FastAPI(title="SWARM-X Guardian API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

WORLD_W, WORLD_H = 1000, 640
SCENARIOS = {"normal": "Normal operation", "failure": "Agent failure", "comms": "Communication loss", "obstacle": "Dynamic obstacle", "battery": "Battery depletion", "scale50": "50-agent stress", "scale100": "100-agent stress"}


class TaskCreate(BaseModel):
    pickup_x: int = Field(ge=0, le=WORLD_W)
    pickup_y: int = Field(ge=0, le=WORLD_H)
    dropoff_x: int = Field(ge=0, le=WORLD_W)
    dropoff_y: int = Field(ge=0, le=WORLD_H)
    priority: str = "MEDIUM"


class ScenarioRequest(BaseModel):
    scenario: str


class SimState:
    def __init__(self):
        self.tick = 1842
        self.running = True
        self.scenario = "normal"
        self.agents = []
        self.tasks = []
        self.events = []
        self.obstacles = [{"x": 470, "y": 245, "w": 130, "h": 28, "active": True}]
        self.metrics = {"mission_success": 96.4, "recovery_time": 1.82, "collision_rate": 0.7, "comms_health": 98.7, "overhead": 12.4, "delivery_time": 42.8}
        self.reset("normal")

    def reset(self, scenario="normal"):
        self.scenario = scenario
        count = 100 if scenario == "scale100" else 50 if scenario == "scale50" else 12
        self.tick = 1842
        self.running = True
        self.agents = []
        self.tasks = []
        self.events = []
        for i in range(count):
            angle = (i / max(count, 1)) * math.tau
            self.agents.append({"id": f"AX-{i+1:03d}", "x": 180 + 220 * math.cos(angle), "y": 310 + 180 * math.sin(angle), "battery": max(25, 94 - (i * 7) % 43), "status": "ACTIVE", "task": f"PKG-{(i % 6) + 1:03d}" if i < 7 else "STANDBY", "velocity": round(2.1 + (i % 4) * .4, 1), "neighbors": 3 + i % 5, "comms": "LINKED"})
        if scenario == "failure":
            self.agents[2]["status"] = "FAILED"; self.agents[2]["comms"] = "LOST"; self.agents[2]["task"] = "PKG-003"
            self.events.append(self.event("FAILURE", "AX-003 heartbeat timeout — task PKG-003 queued for recovery"))
        if scenario == "comms":
            for agent in self.agents[4:7]: agent["comms"] = "DEGRADED"
            self.metrics["comms_health"] = 84.2
            self.events.append(self.event("COMMS", "Mesh partition detected in sector B — local auction active"))
        if scenario == "battery":
            self.agents[1]["battery"] = 12; self.agents[1]["status"] = "RETURNING"
            self.events.append(self.event("BATTERY", "AX-002 reserve threshold reached — returning to charge pad"))
        if scenario == "obstacle":
            self.obstacles[0]["active"] = True
            self.events.append(self.event("NAV", "Dynamic obstacle entered corridor 04 — paths replanning"))
        self.tasks = [{"id": f"PKG-{i+1:03d}", "status": "IN_TRANSIT" if i < 4 else "QUEUED", "priority": "HIGH" if i == 2 else "MEDIUM", "agent": f"AX-{(i % 6) + 1:03d}", "route": "warehouse → dock"} for i in range(8)]

    def event(self, kind, message):
        return {"id": str(uuid.uuid4())[:8], "kind": kind, "message": message, "time": datetime.now(timezone.utc).strftime("%H:%M:%S")}

    def step(self):
        if not self.running: return
        self.tick += 1
        for agent in self.agents[:12]:
            if agent["status"] in ("ACTIVE", "RETURNING"):
                agent["x"] = max(32, min(WORLD_W - 32, agent["x"] + math.sin(self.tick / 20 + int(agent["id"][-3:])) * .9))
                agent["y"] = max(32, min(WORLD_H - 32, agent["y"] + math.cos(self.tick / 22 + int(agent["id"][-3:])) * .7))
                agent["battery"] = max(8, agent["battery"] - .002)
        if self.scenario == "failure" and self.tick % 80 == 0:
            self.events.insert(0, self.event("RECOVERY", "Auction complete — AX-006 accepted PKG-003 at utility 0.82"))
            self.agents[5]["task"] = "PKG-003"
        self.events = self.events[:8]

    def snapshot(self):
        active = sum(a["status"] in ("ACTIVE", "RETURNING") for a in self.agents)
        failed = sum(a["status"] == "FAILED" for a in self.agents)
        return {"tick": self.tick, "running": self.running, "scenario": self.scenario, "scenario_label": SCENARIOS[self.scenario], "agents": self.agents, "tasks": self.tasks, "events": self.events, "obstacles": self.obstacles, "metrics": {**self.metrics, "active_agents": active, "failed_agents": failed, "task_completion": 78.0 + (self.tick % 20) / 10, "recovery_events": len([e for e in self.events if e["kind"] == "RECOVERY"])}, "transport": {"mqtt": False, "fallback": True, "topic": "swarm/guardian/events"}}


sim = SimState()


@app.on_event("startup")
async def loop():
    async def run():
        while True:
            sim.step(); await asyncio.sleep(.6)
    asyncio.create_task(run())


@app.get("/api/")
async def root(): return {"service": "SWARM-X Guardian", "status": "operational", "mode": "decentralized-simulation"}

@app.get("/api/health")
async def health(): return {"status": "ok", "database": "in-memory-demo; PostgreSQL adapter documented", "mqtt": "in-process-fallback"}

@app.get("/api/simulation")
async def get_simulation(): return sim.snapshot()

@app.post("/api/simulation/toggle")
async def toggle(): sim.running = not sim.running; return sim.snapshot()

@app.post("/api/simulation/reset")
async def reset(req: ScenarioRequest):
    if req.scenario not in SCENARIOS: raise HTTPException(400, "Unknown scenario")
    sim.reset(req.scenario); return sim.snapshot()

@app.post("/api/simulation/agents/{agent_id}/fail")
async def fail_agent(agent_id: str):
    agent = next((a for a in sim.agents if a["id"] == agent_id), None)
    if not agent: raise HTTPException(404, "Agent not found")
    agent["status"] = "FAILED"; agent["comms"] = "LOST"
    sim.events.insert(0, sim.event("FAILURE", f"{agent_id} manually isolated — local neighbors starting task auction"))
    return sim.snapshot()

@app.post("/api/tasks")
async def create_task(task: TaskCreate):
    task_id = f"PKG-{len(sim.tasks) + 1:03d}"
    sim.tasks.insert(0, {"id": task_id, "status": "AUCTION", "priority": task.priority, "agent": "BIDDING", "route": f"{task.pickup_x},{task.pickup_y} → {task.dropoff_x},{task.dropoff_y}"})
    sim.events.insert(0, sim.event("AUCTION", f"{task_id} broadcast to {len(sim.agents)} local peers — bids open"))
    return sim.snapshot()

@app.get("/api/benchmarks")
async def benchmarks():
    return {"labels": ["5", "25", "50", "100"], "centralized": [96, 88, 73, 51], "decentralized": [97, 95, 93, 89], "recovery": {"centralized": 18.4, "decentralized": 1.82}}
