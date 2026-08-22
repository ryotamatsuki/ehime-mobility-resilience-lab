"""Deterministic all-or-nothing and BPR user-equilibrium approximation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from common.graph import DirectedGraph, Edge


@dataclass(frozen=True)
class AssignmentParameters:
    alpha: float = 0.15
    beta: float = 4.0
    iterations: int = 25
    convergence: float = 1e-4


@dataclass
class AssignmentResult:
    volumes: dict[str, float]
    travel_times_minutes: dict[str, float]
    unreachable_demand: float
    iterations: int


def bpr_time(edge: Edge, volume: float, alpha: float = 0.15, beta: float = 4.0) -> float:
    if edge.capacity_vph <= 0:
        return float("inf") if volume > 0 else edge.free_flow_minutes
    ratio = max(0.0, volume) / edge.capacity_vph
    return edge.free_flow_minutes * (1.0 + alpha * ratio**beta)


def _cost_function(graph: DirectedGraph, volumes: dict[str, float], params: AssignmentParameters):
    return lambda edge: bpr_time(edge, volumes.get(edge.edge_id, 0.0), params.alpha, params.beta)


def all_or_nothing(
    graph: DirectedGraph,
    od: Iterable[tuple[str, str, float]],
    volumes: dict[str, float] | None = None,
    params: AssignmentParameters | None = None,
    disabled: set[str] | None = None,
) -> tuple[dict[str, float], float]:
    volumes = volumes or {}
    params = params or AssignmentParameters()
    cost = _cost_function(graph, volumes, params)
    result = defaultdict(float)
    unreachable = 0.0
    grouped: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
    for origin, destination, demand in od:
        grouped[origin].append((origin, destination, float(demand)))
    for origin in sorted(grouped):
        distances, previous = graph.dijkstra(origin, cost=cost, disabled=disabled)
        for _, destination, demand in sorted(grouped[origin], key=lambda item: item[1]):
            if demand <= 0:
                continue
            if destination not in distances or distances[destination] == float("inf"):
                unreachable += demand
                continue
            path = graph.path_edges(origin, destination, previous)
            if not path and origin != destination:
                unreachable += demand
                continue
            for edge_id in path:
                result[edge_id] += demand
    return dict(result), unreachable


def assign_user_equilibrium(
    graph: DirectedGraph,
    od: Iterable[tuple[str, str, float]],
    parameters: AssignmentParameters | None = None,
    disabled: set[str] | None = None,
) -> AssignmentResult:
    params = parameters or AssignmentParameters()
    disabled = disabled or set()
    volumes = {edge_id: 0.0 for edge_id in graph.edges}
    iterations = 0
    unreachable = 0.0
    for iteration in range(1, params.iterations + 1):
        aon, unreachable = all_or_nothing(graph, od, volumes, params, disabled)
        step = 1.0 / iteration
        max_change = 0.0
        for edge_id in graph.edges:
            target = aon.get(edge_id, 0.0)
            updated = volumes[edge_id] + step * (target - volumes[edge_id])
            max_change = max(max_change, abs(updated - volumes[edge_id]))
            volumes[edge_id] = updated
        iterations = iteration
        if max_change <= params.convergence:
            break
    times = {
        edge_id: bpr_time(edge, volumes.get(edge_id, 0.0), params.alpha, params.beta)
        for edge_id, edge in graph.edges.items()
        if edge_id not in disabled
    }
    for edge_id in disabled:
        if edge_id in graph.edges:
            times[edge_id] = float("inf")
    return AssignmentResult(volumes, times, unreachable, iterations)
