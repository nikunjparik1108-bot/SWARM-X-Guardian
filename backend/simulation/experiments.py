"""Experiment scenarios — deterministic runs producing real measured results
from the World simulation. No hard-coded numbers.
"""
from __future__ import annotations

import copy
import time
from typing import Any

from .mesh import NetworkState
from .world import World


EXPERIMENT_SCENARIOS: dict[str, dict[str, Any]] = {
    "baseline": {
        "label": "Baseline",
        "description": "Normal operation with a mix of deliveries.",
        "agent_count": 12,
        "duration_ticks": 220,
        "network": NetworkState.NORMAL,
        "failures": [],
        "extra_tasks": 6,
    },
    "agent_failure": {
        "label": "Agent Failure",
        "description": "Single agent fails mid-mission; swarm reassigns work.",
        "agent_count": 12,
        "duration_ticks": 240,
        "network": NetworkState.NORMAL,
        "failures": [(35, 1)],
        "extra_tasks": 6,
    },
    "multi_failure": {
        "label": "Multiple Failures",
        "description": "Two agents fail; swarm redistributes to healthy peers.",
        "agent_count": 14,
        "duration_ticks": 260,
        "network": NetworkState.NORMAL,
        "failures": [(30, 2), (90, 1)],
        "extra_tasks": 8,
    },
    "network_degradation": {
        "label": "Network Degradation",
        "description": "High packet loss stresses the peer mesh.",
        "agent_count": 12,
        "duration_ticks": 240,
        "network": NetworkState.HIGH_PACKET_LOSS,
        "failures": [],
        "extra_tasks": 6,
    },
    "high_load": {
        "label": "High Task Load",
        "description": "Aggressive task injection to test throughput.",
        "agent_count": 14,
        "duration_ticks": 300,
        "network": NetworkState.NORMAL,
        "failures": [],
        "extra_tasks": 14,
    },
}


def _run_single(world: World, config: dict[str, Any]) -> dict[str, Any]:
    world.set_network_state(config["network"])
    for _ in range(config["extra_tasks"]):
        world.spawn_task()
    failure_schedule = list(config["failures"])
    for step in range(config["duration_ticks"]):
        # Trigger scheduled failures
        while failure_schedule and failure_schedule[0][0] == step:
            _, count = failure_schedule.pop(0)
            candidates = [a for a in world.agents if a.status != "FAILED" and a.task_id]
            for a in candidates[:count]:
                world.fail_agent(a.id, reason="scenario")
        world.step()
    metrics = world._metrics()
    return {
        "mission_duration_s": round(world.sim_time, 2),
        "agents": len(world.agents),
        "completed": metrics["completed_tasks"],
        "pending": metrics["pending_tasks"],
        "failures": metrics["failed_agents"],
        "recovered_tasks": metrics["recovered_tasks"],
        "avg_delivery_time": metrics["avg_delivery_time"],
        "avg_recovery_time": metrics["avg_recovery_time"],
        "route_changes": metrics["route_recalculations"],
        "safety_events": metrics["near_miss_events"] + metrics["collision_events"],
        "completion_rate": metrics["mission_completion_rate"],
        "utilization": metrics["agent_utilization"],
        "coordination_cost": metrics["coordination_cost"],
    }


def run_experiment(scenario_id: str, mode: str = "decentralized",
                   agent_count: int | None = None) -> dict[str, Any]:
    if scenario_id not in EXPERIMENT_SCENARIOS:
        raise ValueError(f"Unknown scenario '{scenario_id}'")
    config = copy.deepcopy(EXPERIMENT_SCENARIOS[scenario_id])
    if agent_count is not None:
        config["agent_count"] = agent_count
    world = World(agent_count=config["agent_count"], mode=mode, seed=42)
    started = time.time()
    result = _run_single(world, config)
    result.update({
        "id": f"exp-{int(time.time())}-{scenario_id[:4]}",
        "scenario": scenario_id,
        "scenario_label": config["label"],
        "description": config["description"],
        "mode": mode,
        "agent_count": config["agent_count"],
        "wall_clock_ms": int((time.time() - started) * 1000),
    })
    return result


def run_comparison(scenario_id: str) -> dict[str, Any]:
    """Run the same scenario under centralized + decentralized coordination
    with an identical seed, so results are directly comparable."""
    decentralized = run_experiment(scenario_id, mode="decentralized")
    centralized = run_experiment(scenario_id, mode="centralized")
    return {
        "scenario": scenario_id,
        "scenario_label": EXPERIMENT_SCENARIOS[scenario_id]["label"],
        "decentralized": decentralized,
        "centralized": centralized,
    }
