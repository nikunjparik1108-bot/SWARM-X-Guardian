"""Agent state machine and per-tick behaviour for SWARM-X Guardian.

Each agent owns its own local state, evaluates tasks using a transparent
scoring function, communicates through a peer-to-peer mesh, and can fail /
recover independently of any central controller.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any


class AgentStatus:
    IDLE = "IDLE"
    SEARCHING = "SEARCHING"
    EVALUATING = "EVALUATING"
    NEGOTIATING = "NEGOTIATING"
    ASSIGNED = "ASSIGNED"
    EN_ROUTE = "EN_ROUTE"
    DELIVERING = "DELIVERING"
    RETURNING = "RETURNING"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"

    HEALTHY_ACTIVE = {IDLE, SEARCHING, EVALUATING, NEGOTIATING,
                      ASSIGNED, EN_ROUTE, DELIVERING, RETURNING}


@dataclass
class Agent:
    id: str
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    battery: float = 100.0
    payload_capacity: float = 3.0
    current_payload: float = 0.0
    status: str = AgentStatus.IDLE
    task_id: str | None = None
    neighbors: list[str] = field(default_factory=list)
    comm_quality: float = 1.0
    last_heartbeat: float = 0.0
    health: str = "HEALTHY"
    route: list[tuple[float, float]] = field(default_factory=list)
    home: tuple[float, float] = (80.0, 80.0)
    decision_factors: dict[str, Any] = field(default_factory=dict)
    risk_level: str = "LOW"
    speed: float = 42.0
    delivered_count: int = 0
    recovered_count: int = 0
    failed_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "vx": round(self.vx, 3),
            "vy": round(self.vy, 3),
            "battery": round(self.battery, 1),
            "payload_capacity": self.payload_capacity,
            "current_payload": round(self.current_payload, 2),
            "status": self.status,
            "task_id": self.task_id,
            "neighbors": list(self.neighbors),
            "comm_quality": round(self.comm_quality, 3),
            "last_heartbeat": round(self.last_heartbeat, 2),
            "health": self.health,
            "route": [(round(px, 1), round(py, 1)) for px, py in self.route[:6]],
            "decision_factors": self.decision_factors,
            "risk_level": self.risk_level,
            "speed": self.speed,
            "delivered_count": self.delivered_count,
            "recovered_count": self.recovered_count,
        }

    # ---------------- movement ----------------
    def move_toward(self, target: tuple[float, float], dt: float,
                    world_w: int, world_h: int) -> bool:
        tx, ty = target
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 6.0:
            self.x, self.y = tx, ty
            self.vx = self.vy = 0.0
            return True
        step = self.speed * dt
        step = min(step, dist)
        self.vx = (dx / dist) * step
        self.vy = (dy / dist) * step
        self.x = max(20, min(world_w - 20, self.x + self.vx))
        self.y = max(20, min(world_h - 20, self.y + self.vy))
        return False

    def drain_battery(self, dt: float, active: bool) -> None:
        rate = 0.35 if active else 0.05
        self.battery = max(0.0, self.battery - rate * dt)

    def recharge(self, dt: float) -> None:
        self.battery = min(100.0, self.battery + 6.5 * dt)

    def apply_comm_state(self, quality: float) -> None:
        """Comm quality drives DEGRADED vs healthy substates."""
        self.comm_quality = quality
        if self.status == AgentStatus.FAILED:
            return
        if quality < 0.35 and self.status in AgentStatus.HEALTHY_ACTIVE:
            self.status = AgentStatus.DEGRADED
            self.health = "DEGRADED"
        elif self.status == AgentStatus.DEGRADED and quality >= 0.55:
            # Restore to task-based status
            self.status = AgentStatus.EN_ROUTE if self.task_id else AgentStatus.IDLE
            self.health = "HEALTHY"

    def mark_failed(self, at_tick: float) -> None:
        self.status = AgentStatus.FAILED
        self.health = "OFFLINE"
        self.comm_quality = 0.0
        self.vx = self.vy = 0.0
        self.failed_at = at_tick

    def is_available_for_task(self) -> bool:
        return (
            self.status in {AgentStatus.IDLE, AgentStatus.SEARCHING}
            and self.battery > 25.0
            and self.comm_quality > 0.4
        )
