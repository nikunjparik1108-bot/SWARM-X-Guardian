"""Peer-to-peer communication mesh simulation.

Handles neighbor discovery, link quality (latency, packet loss, signal),
heartbeat monitoring, and network-wide degradation scenarios."""
from __future__ import annotations

import math
import random
from typing import Any

from .agent import Agent, AgentStatus

NEIGHBOR_RADIUS = 260.0
HEARTBEAT_TIMEOUT = 4.0  # seconds


class NetworkState:
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    HIGH_PACKET_LOSS = "HIGH_PACKET_LOSS"
    PARTIAL_PARTITION = "PARTIAL_PARTITION"
    RECOVERED = "RECOVERED"


PROFILE = {
    NetworkState.NORMAL: {"latency": (18, 42), "loss": (0.001, 0.02), "signal": (0.85, 1.0)},
    NetworkState.DEGRADED: {"latency": (60, 140), "loss": (0.05, 0.15), "signal": (0.55, 0.8)},
    NetworkState.HIGH_PACKET_LOSS: {"latency": (80, 220), "loss": (0.2, 0.45), "signal": (0.35, 0.65)},
    NetworkState.PARTIAL_PARTITION: {"latency": (40, 90), "loss": (0.02, 0.08), "signal": (0.6, 0.95)},
    NetworkState.RECOVERED: {"latency": (22, 48), "loss": (0.001, 0.03), "signal": (0.8, 1.0)},
}


class Mesh:
    def __init__(self) -> None:
        self.state: str = NetworkState.NORMAL
        self.links: list[dict[str, Any]] = []
        self.partition_seed: int | None = None
        self.metrics = {"avg_latency": 0.0, "avg_loss": 0.0, "connected_pairs": 0,
                        "partitions": 0}

    def set_state(self, state: str) -> None:
        if state not in PROFILE:
            return
        self.state = state
        if state == NetworkState.PARTIAL_PARTITION:
            self.partition_seed = random.randint(1, 999)
        else:
            self.partition_seed = None

    def _link_metrics(self, dist: float) -> tuple[float, float, float]:
        prof = PROFILE[self.state]
        base_lat = random.uniform(*prof["latency"])
        base_loss = random.uniform(*prof["loss"])
        base_sig = random.uniform(*prof["signal"])
        # Distance attenuation
        atten = min(1.0, dist / NEIGHBOR_RADIUS)
        latency = base_lat * (1.0 + atten * 0.9)
        loss = min(1.0, base_loss + atten * 0.06)
        signal = base_sig * (1.0 - atten * 0.5)
        return latency, loss, signal

    def _partition_group(self, agent_id: str) -> int:
        if self.partition_seed is None:
            return 0
        # Deterministic split by agent numeric id
        try:
            idx = int(agent_id.split("-")[-1])
        except ValueError:
            idx = 0
        return (idx + self.partition_seed) % 2

    def update(self, agents: list[Agent]) -> None:
        self.links.clear()
        living = [a for a in agents if a.status != AgentStatus.FAILED]
        neighbor_map: dict[str, list[str]] = {a.id: [] for a in agents}
        latencies: list[float] = []
        losses: list[float] = []
        signals_by_agent: dict[str, list[float]] = {a.id: [] for a in agents}

        for i in range(len(living)):
            for j in range(i + 1, len(living)):
                a, b = living[i], living[j]
                dist = math.hypot(a.x - b.x, a.y - b.y)
                if dist > NEIGHBOR_RADIUS:
                    continue
                if (self.state == NetworkState.PARTIAL_PARTITION
                        and self._partition_group(a.id) != self._partition_group(b.id)):
                    continue
                latency, loss, signal = self._link_metrics(dist)
                self.links.append({
                    "a": a.id, "b": b.id,
                    "latency": round(latency, 1),
                    "loss": round(loss, 3),
                    "signal": round(signal, 2),
                    "distance": round(dist, 1),
                })
                neighbor_map[a.id].append(b.id)
                neighbor_map[b.id].append(a.id)
                latencies.append(latency)
                losses.append(loss)
                signals_by_agent[a.id].append(signal)
                signals_by_agent[b.id].append(signal)

        for agent in agents:
            agent.neighbors = neighbor_map.get(agent.id, [])
            sigs = signals_by_agent.get(agent.id) or []
            if agent.status == AgentStatus.FAILED:
                agent.apply_comm_state(0.0)
                continue
            quality = (sum(sigs) / len(sigs)) if sigs else 0.15
            # Isolated agent still gets a very low quality (self-only)
            agent.apply_comm_state(quality)

        # partitions = distinct connected components among living agents
        self.metrics = {
            "avg_latency": round(sum(latencies) / len(latencies), 1) if latencies else 0.0,
            "avg_loss": round(sum(losses) / len(losses), 3) if losses else 0.0,
            "connected_pairs": len(self.links),
            "partitions": self._count_partitions(living, neighbor_map),
        }

    def _count_partitions(self, agents: list[Agent],
                          neighbor_map: dict[str, list[str]]) -> int:
        seen: set[str] = set()
        components = 0
        for agent in agents:
            if agent.id in seen:
                continue
            components += 1
            stack = [agent.id]
            while stack:
                node = stack.pop()
                if node in seen:
                    continue
                seen.add(node)
                stack.extend(neighbor_map.get(node, []))
        return max(components, 1)

    def detect_timeouts(self, agents: list[Agent], now: float) -> list[str]:
        """Return list of agent IDs that a *neighbor* would detect as timed out."""
        newly_failed: list[str] = []
        for agent in agents:
            if agent.status == AgentStatus.FAILED:
                continue
            if now - agent.last_heartbeat > HEARTBEAT_TIMEOUT and agent.last_heartbeat > 0:
                # Only "detected" if at least one neighbor is around to notice
                if agent.neighbors:
                    newly_failed.append(agent.id)
        return newly_failed
