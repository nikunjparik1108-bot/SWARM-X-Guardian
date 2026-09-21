"""FastAPI server for SWARM-X Guardian.

Wraps the simulation.World with a REST API used by the React operations
console. All metrics come from real simulation state — no hardcoded values.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

from integrations import copilot, storage
from simulation import World, WORLD_H, WORLD_W
from simulation.experiments import EXPERIMENT_SCENARIOS, run_comparison, run_experiment
from simulation.mesh import NetworkState

logger = logging.getLogger("swarm.server")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="SWARM-X Guardian API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

world = World(agent_count=12, mode="decentralized")

# --- Persistence: MongoDB for file records + copilot history ---------
mongo_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = mongo_client[os.environ["DB_NAME"]]
files_col = db["swarm_files"]
copilot_col = db["swarm_copilot"]


@app.on_event("startup")
async def _startup() -> None:
    storage.init_storage()  # cache storage_key once
    try:
        await files_col.create_index([("category", 1), ("created_at", -1)])
        await files_col.create_index([("ref_id", 1)])
    except Exception as e:  # noqa: BLE001
        logger.warning(f"index creation skipped: {e}")


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


# ============================================================
# File & media storage (Emergent Object Storage)
# ============================================================
class CopilotAsk(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


VALID_CATEGORIES = {"delivery", "incident", "recon"}


@app.get("/api/integrations/status")
async def integrations_status():
    return {
        "storage_enabled": storage.is_enabled(),
        "copilot_enabled": copilot.is_enabled(),
        "model": copilot.PERPLEXITY_PRESET if copilot.is_enabled() else None,
    }


@app.post("/api/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form("recon"),
    ref_id: str = Form(""),
    caption: str = Form(""),
):
    if not storage.is_enabled():
        raise HTTPException(status_code=503, detail="Object storage is not configured on the server.")
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"category must be one of {sorted(VALID_CATEGORIES)}")
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > storage.MAX_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB")
    try:
        path, fid, content_type = storage.build_path(category, file.filename or "upload")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    try:
        result = storage.put_object(path, data, content_type)
    except Exception as e:  # noqa: BLE001
        logger.exception("upload failed")
        raise HTTPException(status_code=502, detail=f"Upload failed: {e}") from e

    record = {
        "id": fid,
        "category": category,
        "ref_id": ref_id or None,
        "caption": caption or None,
        "storage_path": result.get("path", path),
        "original_filename": file.filename,
        "content_type": content_type,
        "size": result.get("size", len(data)),
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await files_col.insert_one(record.copy())
    record.pop("_id", None)
    world.log("FILE", f"{category} upload · {file.filename}")
    return record


@app.get("/api/files")
async def list_files(category: str | None = Query(None), ref_id: str | None = Query(None), limit: int = 60):
    q: dict[str, Any] = {"is_deleted": False}
    if category:
        q["category"] = category
    if ref_id:
        q["ref_id"] = ref_id
    cursor = files_col.find(q, {"_id": 0}).sort("created_at", -1).limit(min(limit, 200))
    return {"files": [doc async for doc in cursor]}


@app.get("/api/files/{fid}/download")
async def download_file(fid: str):
    rec = await files_col.find_one({"id": fid, "is_deleted": False}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        data, ct = storage.get_object(rec["storage_path"])
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Download failed: {e}") from e
    return Response(content=data, media_type=rec.get("content_type") or ct,
                    headers={"Cache-Control": "private, max-age=300"})


@app.delete("/api/files/{fid}")
async def delete_file(fid: str):
    r = await files_col.update_one({"id": fid}, {"$set": {"is_deleted": True}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="File not found")
    return {"ok": True}


# ============================================================
# Mission Copilot (Perplexity)
# ============================================================
@app.post("/api/copilot/ask")
async def copilot_ask(payload: CopilotAsk):
    snapshot = world.snapshot()
    result = await copilot.ask(payload.question, snapshot)
    doc = {
        "question": payload.question,
        "answer": result.get("answer"),
        "citations": result.get("citations", []),
        "model": result.get("model"),
        "tick": snapshot.get("tick"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await copilot_col.insert_one(doc.copy())
    except Exception:  # noqa: BLE001
        pass
    world.log("COPILOT", f"Analyst asked: {payload.question[:60]}…")
    return result


@app.get("/api/copilot/history")
async def copilot_history(limit: int = 20):
    cursor = copilot_col.find({}, {"_id": 0}).sort("created_at", -1).limit(min(limit, 100))
    return {"items": [doc async for doc in cursor]}
