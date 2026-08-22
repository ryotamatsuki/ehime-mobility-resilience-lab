"""Small deterministic directed graph implementation for analysis and tests."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from math import inf
from typing import Callable, Iterable


@dataclass(frozen=True)
class Edge:
    edge_id: str
    u: str
    v: str
    length_km: float
    free_speed_kmh: float
    capacity_vph: float
    mode: str = "road"
    attributes: dict[str, object] = field(default_factory=dict)

    @property
    def free_flow_minutes(self) -> float:
        if self.free_speed_kmh <= 0:
            raise ValueError("free_speed_kmh must be positive")
        return self.length_km / self.free_speed_kmh * 60.0


class DirectedGraph:
    def __init__(self) -> None:
        self.edges: dict[str, Edge] = {}
        self.out_edges: dict[str, list[str]] = {}

    @property
    def nodes(self) -> set[str]:
        return set(self.out_edges)

    def add_edge(self, edge: Edge) -> None:
        if edge.edge_id in self.edges:
            raise ValueError(f"duplicate edge_id: {edge.edge_id}")
        self.edges[edge.edge_id] = edge
        self.out_edges.setdefault(edge.u, []).append(edge.edge_id)
        self.out_edges.setdefault(edge.v, [])
        self.out_edges[edge.u].sort()

    def dijkstra(
        self,
        source: str,
        cost: Callable[[Edge], float] | None = None,
        disabled: set[str] | None = None,
    ) -> tuple[dict[str, float], dict[str, str | None]]:
        if source not in self.out_edges:
            return {}, {}
        disabled = disabled or set()
        cost = cost or (lambda edge: edge.free_flow_minutes)
        distances = {node: inf for node in self.out_edges}
        previous: dict[str, str | None] = {node: None for node in self.out_edges}
        distances[source] = 0.0
        heap: list[tuple[float, str]] = [(0.0, source)]
        while heap:
            current_distance, node = heapq.heappop(heap)
            if current_distance != distances[node]:
                continue
            for edge_id in self.out_edges.get(node, []):
                if edge_id in disabled:
                    continue
                edge = self.edges[edge_id]
                edge_cost = cost(edge)
                if edge_cost < 0 or edge_cost == inf:
                    continue
                candidate = current_distance + edge_cost
                if candidate < distances[edge.v] - 1e-12:
                    distances[edge.v] = candidate
                    previous[edge.v] = edge_id
                    heapq.heappush(heap, (candidate, edge.v))
        return distances, previous

    def path_edges(
        self,
        source: str,
        target: str,
        previous: dict[str, str | None],
    ) -> list[str]:
        if source == target:
            return []
        path: list[str] = []
        node = target
        visited: set[str] = set()
        while node != source:
            if node in visited:
                return []
            visited.add(node)
            edge_id = previous.get(node)
            if edge_id is None:
                return []
            path.append(edge_id)
            node = self.edges[edge_id].u
        path.reverse()
        return path

    def reachable(self, source: str, max_cost: float) -> dict[str, float]:
        distances, _ = self.dijkstra(source)
        return {node: value for node, value in distances.items() if value <= max_cost}

    def validate(self) -> list[str]:
        errors: list[str] = []
        for edge_id, edge in sorted(self.edges.items()):
            if edge_id != edge.edge_id:
                errors.append(f"edge key mismatch: {edge_id}")
            if edge.u not in self.out_edges or edge.v not in self.out_edges:
                errors.append(f"missing endpoint: {edge_id}")
            if edge.length_km <= 0:
                errors.append(f"non-positive length: {edge_id}")
            if edge.free_speed_kmh <= 0:
                errors.append(f"non-positive speed: {edge_id}")
            if edge.capacity_vph < 0:
                errors.append(f"negative capacity: {edge_id}")
        return errors

    def sorted_edges(self) -> Iterable[Edge]:
        return (self.edges[edge_id] for edge_id in sorted(self.edges))
