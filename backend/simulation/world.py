"""Simulation world / controller.

Owns agents, tasks, mesh, obstacles, events, and computed metrics.
Runs a deterministic tick loop; all metrics derive from real state.
"""
from __future__ import annotations

import math
import random
import time
import uuid
from collections import deque
from typing import Any

from .agent import Agent, AgentStatus
from .allocator import run_auction, score_task
from .mesh import Mesh, NetworkState
from .task import Task, TaskStatus

WORLD_W = 1000
WORLD_H = 640
HOME_BASE = (80.0, 80.0)
DEPOT_A = (140.0, 520.0)
DEPOT_B = (860.0, 120.0)
CHARGE_PAD = (60.0, WORLD_H - 60.0)


def _label_time(ts: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts))


class World:
    def __init__(self, agent_count: int = 12, mode: str = "decentralized",
                 seed: int | None = 7) -> None:
        self.rng = random.Random(seed)
        self.tick = 0
        self.sim_time = 0.0
        self.dt = 0.4
        self.running = True
        self.mode = mode  # "decentralized" | "centralized"
        self.scenario = "normal"
        self.mesh = Mesh()
        self.agents: list[Agent] = []
        self.tasks: list[Task] = []
        self.events: deque[dict[str, Any]] = deque(maxlen=400)
        self.obstacles: list[dict[str, Any]] = [
            {"id": "OBS-01", "x": 440, "y": 230, "w": 180, "h": 40, "active": True,
             "label": "STATIC OBSTACLE"},
        ]
        self.recovery_history: list[dict[str, Any]] = []
        self.route_recalculations = 0
        self.collision_events = 0
        self.near_miss_events = 0
        self.completed_tasks: list[Task] = []
        self.central_load = 0.0  # cumulative coordination cost in centralized mode
        self._reset(agent_count)

    # -------------- lifecycle --------------
    def _reset(self, count: int) -> None:
        self.agents = []
        self.tasks = []
        self.events.clear()
        self.completed_tasks = []
        self.recovery_history = []
        self.route_recalculations = 0
        self.collision_events = 0
        self.near_miss_events = 0
        self.central_load = 0.0
        self.tick = 0
        self.sim_time = 0.0
        self.running = True
        cols = max(3, int(math.sqrt(count) * 1.6))
        for i in range(count):
            row, col = divmod(i, cols)
            x = 90 + col * (WORLD_W - 220) / max(cols - 1, 1)
            y = 110 + row * 90
            y = max(60, min(WORLD_H - 60, y))
            agent = Agent(
                id=f"DR-{i+1:03d}",
                x=x, y=y,
                battery=95.0 - self.rng.uniform(0, 20),
                payload_capacity=self.rng.choice([2.5, 3.0, 3.5]),
                speed=36.0 + self.rng.uniform(0, 14),
                home=(x, y),
            )
            agent.last_heartbeat = self.sim_time
            self.agents.append(agent)
        self.mesh.set_state(NetworkState.NORMAL)
        self.mesh.update(self.agents)
        self.log("SYSTEM", f"Swarm initialized with {count} agents in {self.mode} mode")

    def reset(self, agent_count: int | None = None, mode: str | None = None,
              scenario: str = "normal") -> None:
        if mode:
            self.mode = mode
        if agent_count is None:
            agent_count = len(self.agents) or 12
        self.scenario = scenario
        self._reset(agent_count)
        self.apply_scenario(scenario)

    def apply_scenario(self, scenario: str) -> None:
        self.scenario = scenario
        if scenario == "baseline" or scenario == "normal":
            self.mesh.set_state(NetworkState.NORMAL)
            for _ in range(3):
                self.spawn_task()
        elif scenario == "agent_failure":
            for _ in range(4):
                self.spawn_task()
            # schedule failure after short delay
            self._pending_failure = self.sim_time + 6.0
        elif scenario == "multi_failure":
            for _ in range(6):
                self.spawn_task()
            self._pending_multi_failure = self.sim_time + 5.0
        elif scenario == "network_degradation":
            for _ in range(5):
                self.spawn_task()
            self.mesh.set_state(NetworkState.HIGH_PACKET_LOSS)
            self.log("NETWORK", "Injected HIGH_PACKET_LOSS network scenario")
        elif scenario == "high_load":
            for _ in range(12):
                self.spawn_task()
        elif scenario == "battery":
            for agent in self.agents[:2]:
                agent.battery = 18.0
            for _ in range(3):
                self.spawn_task()
        elif scenario == "obstacle":
            self.obstacles.append({"id": f"OBS-{len(self.obstacles)+1:02d}",
                                   "x": 620, "y": 380, "w": 90, "h": 90,
                                   "active": True, "label": "DYNAMIC OBSTACLE"})
            for _ in range(3):
                self.spawn_task()
        else:
            for _ in range(3):
                self.spawn_task()

    # -------------- tasks --------------
    def spawn_task(self, pickup: tuple[float, float] | None = None,
                   dropoff: tuple[float, float] | None = None,
                   priority: str = "MEDIUM",
                   payload_weight: float | None = None) -> Task:
        task_id = f"DEL-{len(self.tasks) + len(self.completed_tasks) + 1:03d}"
        if pickup is None:
            pickup = (self.rng.uniform(120, 320), self.rng.uniform(120, WORLD_H - 120))
        if dropoff is None:
            dropoff = (self.rng.uniform(WORLD_W - 320, WORLD_W - 120),
                       self.rng.uniform(120, WORLD_H - 120))
        weight = payload_weight if payload_weight is not None else round(self.rng.uniform(0.6, 2.6), 2)
        task = Task(id=task_id, pickup=pickup, dropoff=dropoff, priority=priority,
                    payload_weight=weight, created_at=self.sim_time,
                    status=TaskStatus.AUCTIONING)
        self.tasks.append(task)
        self.log("TASK", f"New delivery task {task_id} broadcast ({priority}, {weight}kg)")
        return task

    def _eligible_bidders(self, task: Task) -> list[Agent]:
        return [a for a in self.agents if a.is_available_for_task()
                and task.payload_weight <= a.payload_capacity]

    def _run_auction_for(self, task: Task) -> None:
        candidates = self._eligible_bidders(task)
        if not candidates:
            return
        # Centralized: only the "controller" (first healthy agent) runs the scoring.
        if self.mode == "centralized":
            self.central_load += 1.0
            controller = next((a for a in self.agents
                               if a.status != AgentStatus.FAILED), None)
            if controller is None or controller.comm_quality < 0.3:
                # Central controller can't reach agents — mission stalls.
                return
            winner, bids = run_auction(task, candidates, mode="centralized")
        else:
            winner, bids = run_auction(task, candidates, mode="decentralized")
        if winner is None:
            return
        task.assigned_agent = winner.id
        task.status = TaskStatus.ASSIGNED
        task.assigned_at = self.sim_time
        task.bids = bids
        winner.task_id = task.id
        winner.status = AgentStatus.ASSIGNED
        winner.route = [task.pickup, task.dropoff]
        winner.decision_factors = bids[0]["factors"] if bids else {}
        self.log("AUCTION",
                 f"{winner.id} accepted {task.id} at score {bids[0]['score']:.2f}")

    # -------------- failure / recovery --------------
    def fail_agent(self, agent_id: str, reason: str = "manual") -> Agent | None:
        agent = next((a for a in self.agents if a.id == agent_id), None)
        if not agent or agent.status == AgentStatus.FAILED:
            return None
        agent.mark_failed(self.sim_time)
        self.log("FAILURE", f"{agent.id} failed ({reason}) — heartbeat lost")
        # Release its current task
        if agent.task_id:
            task = next((t for t in self.tasks if t.id == agent.task_id), None)
            if task:
                task.status = TaskStatus.INTERRUPTED
                task.assigned_agent = None
                task.reassignments += 1
                self.log("RECOVERY", f"{task.id} released for re-auction (interrupted)")
                # Reassign immediately
                candidates = self._eligible_bidders(task)
                winner, bids = run_auction(task, candidates, mode=self.mode)
                if winner:
                    task.status = TaskStatus.ASSIGNED
                    task.assigned_agent = winner.id
                    task.assigned_at = self.sim_time
                    task.bids = bids
                    winner.task_id = task.id
                    winner.status = AgentStatus.ASSIGNED
                    winner.route = [task.pickup, task.dropoff]
                    winner.decision_factors = bids[0]["factors"] if bids else {}
                    winner.recovered_count += 1
                    recovery_time = self.sim_time - agent.failed_at
                    self.recovery_history.append({
                        "task_id": task.id,
                        "failed_agent": agent.id,
                        "replacement": winner.id,
                        "recovery_time": round(recovery_time, 2),
                        "at": self.sim_time,
                    })
                    self.log("RECOVERY",
                             f"{winner.id} accepted {task.id} — recovery {recovery_time:.2f}s")
        return agent

    # -------------- comms scenarios --------------
    def set_network_state(self, state: str) -> None:
        self.mesh.set_state(state)
        self.log("NETWORK", f"Network state → {state}")

    # -------------- main tick --------------
    def step(self) -> None:
        if not self.running:
            return
        self.tick += 1
        self.sim_time += self.dt

        # Pending scenario events
        pending = getattr(self, "_pending_failure", None)
        if pending and self.sim_time >= pending:
            target = next((a for a in self.agents if a.task_id), None)
            if target:
                self.fail_agent(target.id, reason="scenario_injection")
            self._pending_failure = None
        pending_multi = getattr(self, "_pending_multi_failure", None)
        if pending_multi and self.sim_time >= pending_multi:
            targets = [a for a in self.agents if a.task_id][:2]
            for t in targets:
                self.fail_agent(t.id, reason="multi_failure_scenario")
            self._pending_multi_failure = None

        # Update mesh + neighbors + comm quality
        self.mesh.update(self.agents)

        # Heartbeats
        for agent in self.agents:
            if agent.status != AgentStatus.FAILED:
                # Skip heartbeat with probability proportional to packet loss
                loss = self.mesh.metrics["avg_loss"]
                if self.rng.random() > loss:
                    agent.last_heartbeat = self.sim_time

        # Detect timed-out agents by neighbor observation
        for stale_id in self.mesh.detect_timeouts(self.agents, self.sim_time):
            agent = next((a for a in self.agents if a.id == stale_id), None)
            if agent and agent.status != AgentStatus.FAILED:
                self.fail_agent(agent.id, reason="heartbeat_timeout")

        # Auction any AUCTIONING tasks
        for task in self.tasks:
            if task.status == TaskStatus.AUCTIONING:
                self._run_auction_for(task)

        # Move agents / progress their state machine
        self._advance_agents()

        # Safety / collision constraints
        self._enforce_safety()

        # Periodic task drip in high_load / baseline scenarios
        if self.scenario in {"baseline", "normal"} and self.tick % 80 == 0:
            self.spawn_task()
        if self.scenario == "high_load" and self.tick % 30 == 0 and len(
                [t for t in self.tasks if t.status != TaskStatus.DELIVERED]) < 20:
            self.spawn_task()

    def _advance_agents(self) -> None:
        for agent in self.agents:
            if agent.status == AgentStatus.FAILED:
                continue
            # Battery critical → return home to recharge
            if agent.battery < 20 and agent.status != AgentStatus.RETURNING:
                agent.status = AgentStatus.RETURNING
                agent.task_id = None
                self.log("BATTERY", f"{agent.id} reserve threshold — returning to pad")

            if agent.status == AgentStatus.RETURNING:
                arrived = agent.move_toward(CHARGE_PAD, self.dt, WORLD_W, WORLD_H)
                agent.drain_battery(self.dt, active=True)
                if arrived:
                    agent.status = AgentStatus.RECOVERING
                continue
            if agent.status == AgentStatus.RECOVERING:
                agent.recharge(self.dt)
                if agent.battery >= 92.0:
                    agent.status = AgentStatus.IDLE
                    self.log("SYSTEM", f"{agent.id} recharged and rejoined swarm")
                continue

            task = next((t for t in self.tasks if t.id == agent.task_id), None) \
                if agent.task_id else None

            if agent.status == AgentStatus.ASSIGNED and task:
                agent.status = AgentStatus.EN_ROUTE
                self.log("NAV", f"{agent.id} en-route to pickup for {task.id}")

            if agent.status == AgentStatus.EN_ROUTE and task:
                arrived = agent.move_toward(task.pickup, self.dt, WORLD_W, WORLD_H)
                agent.drain_battery(self.dt, active=True)
                if arrived:
                    agent.status = AgentStatus.DELIVERING
                    agent.current_payload = task.payload_weight
                    task.status = TaskStatus.IN_TRANSIT
                    task.picked_up_at = self.sim_time
                    self.log("NAV", f"{agent.id} picked up {task.id} — delivering")
                continue

            if agent.status == AgentStatus.DELIVERING and task:
                arrived = agent.move_toward(task.dropoff, self.dt, WORLD_W, WORLD_H)
                agent.drain_battery(self.dt, active=True)
                if arrived:
                    task.status = TaskStatus.DELIVERED
                    task.delivered_at = self.sim_time
                    agent.delivered_count += 1
                    agent.current_payload = 0.0
                    agent.status = AgentStatus.IDLE
                    agent.task_id = None
                    self.completed_tasks.append(task)
                    self.log("DELIVERY", f"{agent.id} delivered {task.id}")
                continue

            if agent.status in {AgentStatus.IDLE, AgentStatus.SEARCHING}:
                agent.drain_battery(self.dt, active=False)

    def _enforce_safety(self) -> None:
        """Minimum-separation constraint. If two moving agents get too close
        the lower-id one slows / detours by nudging perpendicular to their
        connecting vector, and we count a near-miss + route recalc."""
        moving = [a for a in self.agents
                  if a.status in {AgentStatus.EN_ROUTE, AgentStatus.DELIVERING,
                                  AgentStatus.RETURNING}]
        min_sep = 28.0
        for i in range(len(moving)):
            for j in range(i + 1, len(moving)):
                a, b = moving[i], moving[j]
                dx, dy = b.x - a.x, b.y - a.y
                dist = math.hypot(dx, dy)
                if dist < 6.0:
                    self.collision_events += 1
                    self.log("SAFETY", f"Collision-avoidance triggered between {a.id} and {b.id}")
                if dist < min_sep and dist > 0:
                    # perpendicular nudge to break tie
                    push = (min_sep - dist) * 0.5
                    nx, ny = -dy / dist, dx / dist
                    a.x -= nx * push
                    a.y -= ny * push
                    b.x += nx * push
                    b.y += ny * push
                    self.near_miss_events += 1
                    self.route_recalculations += 1

    # -------------- metrics --------------
    def _metrics(self) -> dict[str, Any]:
        active = sum(1 for a in self.agents
                     if a.status in AgentStatus.HEALTHY_ACTIVE)
        failed = sum(1 for a in self.agents if a.status == AgentStatus.FAILED)
        degraded = sum(1 for a in self.agents if a.status == AgentStatus.DEGRADED)
        recovering = sum(1 for a in self.agents if a.status == AgentStatus.RECOVERING)
        total = len(self.tasks) + len(self.completed_tasks)
        completed = len(self.completed_tasks)
        pending = sum(1 for t in self.tasks if t.status != TaskStatus.DELIVERED)
        auctioning = sum(1 for t in self.tasks if t.status == TaskStatus.AUCTIONING)
        interrupted = sum(1 for t in self.tasks if t.status == TaskStatus.INTERRUPTED)
        recovered_tasks = len([r for r in self.recovery_history])
        avg_delivery = 0.0
        if self.completed_tasks:
            deltas = [(t.delivered_at or 0) - t.created_at for t in self.completed_tasks]
            avg_delivery = round(sum(deltas) / len(deltas), 2)
        avg_recovery = 0.0
        if self.recovery_history:
            avg_recovery = round(
                sum(r["recovery_time"] for r in self.recovery_history)
                / len(self.recovery_history), 2)
        utilization = 0.0
        if self.agents:
            busy = sum(1 for a in self.agents
                       if a.status in {AgentStatus.EN_ROUTE, AgentStatus.DELIVERING,
                                       AgentStatus.ASSIGNED})
            utilization = round(busy / len(self.agents) * 100, 1)
        completion_rate = round(completed / total * 100, 1) if total else 0.0
        return {
            "active_agents": active,
            "failed_agents": failed,
            "degraded_agents": degraded,
            "recovering_agents": recovering,
            "total_tasks": total,
            "completed_tasks": completed,
            "pending_tasks": pending,
            "auctioning_tasks": auctioning,
            "interrupted_tasks": interrupted,
            "recovered_tasks": recovered_tasks,
            "avg_delivery_time": avg_delivery,
            "avg_recovery_time": avg_recovery,
            "route_recalculations": self.route_recalculations,
            "collision_events": self.collision_events,
            "near_miss_events": self.near_miss_events,
            "mission_completion_rate": completion_rate,
            "agent_utilization": utilization,
            "avg_latency_ms": self.mesh.metrics["avg_latency"],
            "avg_packet_loss": self.mesh.metrics["avg_loss"],
            "connected_pairs": self.mesh.metrics["connected_pairs"],
            "partitions": self.mesh.metrics["partitions"],
            "coordination_cost": round(self.central_load, 2),
        }

    def log(self, kind: str, message: str) -> None:
        self.events.appendleft({
            "id": uuid.uuid4().hex[:8],
            "kind": kind,
            "message": message,
            "time": _label_time(time.time()),
            "sim_time": round(self.sim_time, 2),
            "tick": self.tick,
        })

    def snapshot(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "sim_time": round(self.sim_time, 2),
            "running": self.running,
            "mode": self.mode,
            "scenario": self.scenario,
            "network_state": self.mesh.state,
            "world": {"w": WORLD_W, "h": WORLD_H, "charge_pad": list(CHARGE_PAD)},
            "agents": [a.to_dict() for a in self.agents],
            "tasks": [t.to_dict() for t in self.tasks],
            "completed_tasks": [t.to_dict() for t in self.completed_tasks[-30:]],
            "obstacles": self.obstacles,
            "links": self.mesh.links,
            "events": list(self.events)[:80],
            "metrics": self._metrics(),
            "recovery_history": self.recovery_history[-10:],
        }
