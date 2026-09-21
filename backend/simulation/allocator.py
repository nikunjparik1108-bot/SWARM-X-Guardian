"""Transparent utility-based scoring + auction for peer task allocation."""
from __future__ import annotations

import math
from typing import Any

from .agent import Agent
from .task import Task, PRIORITY_WEIGHT

# Configurable weights (must sum to ~1.0)
WEIGHTS = {
    "distance": 0.30,
    "battery": 0.25,
    "payload": 0.15,
    "workload": 0.10,
    "eta": 0.10,
    "priority": 0.10,
}

MAX_DIST = 1400.0  # world diagonal-ish


def _label(value: float) -> str:
    if value >= 0.75:
        return "GOOD"
    if value >= 0.5:
        return "OK"
    if value >= 0.3:
        return "LOW"
    return "POOR"


def score_task(agent: Agent, task: Task, active_task_count: int = 0) -> tuple[float, dict[str, Any]]:
    """Return (score, decision_factors) for agent bidding on task."""
    if not agent.is_available_for_task():
        return 0.0, {"eligible": False, "reason": "unavailable"}

    dist = math.hypot(task.pickup[0] - agent.x, task.pickup[1] - agent.y)
    distance_factor = max(0.0, 1.0 - dist / MAX_DIST)
    battery_factor = max(0.0, min(1.0, (agent.battery - 20.0) / 80.0))
    payload_factor = 1.0 if task.payload_weight <= agent.payload_capacity else 0.0
    eta = dist / max(agent.speed, 1.0)  # simulated seconds
    eta_factor = max(0.0, 1.0 - eta / 60.0)
    workload_factor = max(0.0, 1.0 - active_task_count / 3.0)
    priority_factor = PRIORITY_WEIGHT.get(task.priority, 0.6)

    score = (
        WEIGHTS["distance"] * distance_factor
        + WEIGHTS["battery"] * battery_factor
        + WEIGHTS["payload"] * payload_factor
        + WEIGHTS["workload"] * workload_factor
        + WEIGHTS["eta"] * eta_factor
        + WEIGHTS["priority"] * priority_factor
    )
    # Comm quality gates the bid — noisy links produce weaker bids.
    score *= 0.5 + 0.5 * agent.comm_quality

    factors = {
        "eligible": True,
        "score": round(score, 3),
        "distance_km": round(dist / 100.0, 2),
        "distance": _label(distance_factor),
        "battery": _label(battery_factor),
        "payload": "COMPATIBLE" if payload_factor > 0 else "OVER_CAPACITY",
        "eta_s": round(eta, 1),
        "eta": _label(eta_factor),
        "risk": "LOW" if agent.comm_quality > 0.7 else "MEDIUM",
        "workload": _label(workload_factor),
        "priority": task.priority,
        "weights": WEIGHTS,
    }
    return score, factors


def run_auction(task: Task, candidates: list[Agent],
                mode: str = "decentralized") -> tuple[Agent | None, list[dict[str, Any]]]:
    """Return winning agent + bid log. In centralized mode, one node picks;
    in decentralized mode, each eligible peer scores locally and highest bid wins.

    Both modes use identical scoring so results are comparable — the difference
    is topological (single decision maker vs distributed) which is reflected in
    added coordination cost + failure surface tracked by the world."""
    bids: list[dict[str, Any]] = []
    best: tuple[float, Agent | None] = (-1.0, None)
    for agent in candidates:
        score, factors = score_task(agent, task)
        if score > 0:
            bids.append({"agent": agent.id, "score": round(score, 3),
                          "factors": factors})
        if score > best[0]:
            best = (score, agent)
    bids.sort(key=lambda b: b["score"], reverse=True)
    return best[1], bids
