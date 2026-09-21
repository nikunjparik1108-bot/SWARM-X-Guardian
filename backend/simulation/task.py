"""Task lifecycle for SWARM-X Guardian."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class TaskStatus:
    PENDING = "PENDING"
    AUCTIONING = "AUCTIONING"
    ASSIGNED = "ASSIGNED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    INTERRUPTED = "INTERRUPTED"


PRIORITY_WEIGHT = {"LOW": 0.4, "MEDIUM": 0.7, "HIGH": 1.0}


@dataclass
class Task:
    id: str
    pickup: tuple[float, float]
    dropoff: tuple[float, float]
    priority: str = "MEDIUM"
    payload_weight: float = 1.2
    deadline: float = 120.0  # seconds from creation
    status: str = TaskStatus.PENDING
    assigned_agent: str | None = None
    created_at: float = 0.0
    assigned_at: float | None = None
    delivered_at: float | None = None
    picked_up_at: float | None = None
    reassignments: int = 0
    bids: list[dict[str, Any]] = field(default_factory=list)

    def priority_weight(self) -> float:
        return PRIORITY_WEIGHT.get(self.priority, 0.6)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pickup": [round(self.pickup[0], 1), round(self.pickup[1], 1)],
            "dropoff": [round(self.dropoff[0], 1), round(self.dropoff[1], 1)],
            "priority": self.priority,
            "payload_weight": self.payload_weight,
            "deadline": self.deadline,
            "status": self.status,
            "assigned_agent": self.assigned_agent,
            "created_at": round(self.created_at, 2),
            "assigned_at": round(self.assigned_at, 2) if self.assigned_at else None,
            "delivered_at": round(self.delivered_at, 2) if self.delivered_at else None,
            "reassignments": self.reassignments,
            "bids": self.bids[-5:],
        }
