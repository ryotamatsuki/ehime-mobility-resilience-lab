"""Deterministic gravity and IPF utilities with explicit constraints."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


class InfeasibleConstraints(ValueError):
    """Raised when OD constraints cannot be satisfied."""


def _check_targets(origins: list[str], destinations: list[str], row: list[float], col: list[float]) -> None:
    if len(origins) != len(row) or len(destinations) != len(col):
        raise InfeasibleConstraints("target length does not match zone length")
    if any(value < 0 for value in row + col):
        raise InfeasibleConstraints("OD targets must be non-negative")
    if abs(sum(row) - sum(col)) > 1e-9:
        raise InfeasibleConstraints("origin and destination totals differ")


def gravity_seed(
    origins: list[str],
    destinations: list[str],
    origin_targets: list[float],
    destination_targets: list[float],
    impedance: dict[tuple[str, str], float],
    beta: float,
    structural_zeros: set[tuple[str, str]] | None = None,
) -> dict[tuple[str, str], float]:
    _check_targets(origins, destinations, origin_targets, destination_targets)
    structural_zeros = structural_zeros or set()
    seed: dict[tuple[str, str], float] = {}
    for i, origin in enumerate(origins):
        for j, destination in enumerate(destinations):
            if (origin, destination) in structural_zeros:
                seed[(origin, destination)] = 0.0
                continue
            value = impedance.get((origin, destination))
            if value is None or value < 0:
                raise InfeasibleConstraints(f"missing or negative impedance for {origin}/{destination}")
            seed[(origin, destination)] = math.exp(-beta * value)
    return seed


def ipf(
    origins: list[str],
    destinations: list[str],
    origin_targets: list[float],
    destination_targets: list[float],
    seed: dict[tuple[str, str], float],
    max_iterations: int = 5000,
    tolerance: float = 1e-10,
) -> dict[tuple[str, str], float]:
    _check_targets(origins, destinations, origin_targets, destination_targets)
    values = {
        (origin, destination): max(0.0, float(seed.get((origin, destination), 0.0)))
        for origin in origins
        for destination in destinations
    }
    for origin, target in zip(origins, origin_targets):
        if target > 0 and sum(values[(origin, destination)] for destination in destinations) == 0:
            raise InfeasibleConstraints(f"origin {origin} has no feasible destination")
    for destination, target in zip(destinations, destination_targets):
        if target > 0 and sum(values[(origin, destination)] for origin in origins) == 0:
            raise InfeasibleConstraints(f"destination {destination} has no feasible origin")
    for _ in range(max_iterations):
        for origin, target in zip(origins, origin_targets):
            total = sum(values[(origin, destination)] for destination in destinations)
            if total == 0 and target == 0:
                continue
            if total == 0:
                raise InfeasibleConstraints(f"origin {origin} is structurally zero")
            factor = target / total
            for destination in destinations:
                values[(origin, destination)] *= factor
        for destination, target in zip(destinations, destination_targets):
            total = sum(values[(origin, destination)] for origin in origins)
            if total == 0 and target == 0:
                continue
            if total == 0:
                raise InfeasibleConstraints(f"destination {destination} is structurally zero")
            factor = target / total
            for origin in origins:
                values[(origin, destination)] *= factor
        error = max(
            [
                abs(sum(values[(origin, destination)] for destination in destinations) - target)
                for origin, target in zip(origins, origin_targets)
            ]
            + [
                abs(sum(values[(origin, destination)] for origin in origins) - target)
                for destination, target in zip(destinations, destination_targets)
            ]
        )
        if error <= tolerance:
            return values
    raise InfeasibleConstraints("IPF did not converge")


def constrained_ipf(
    origins: list[str],
    destinations: list[str],
    origin_targets: list[float],
    destination_targets: list[float],
    origin_groups: dict[str, str],
    destination_groups: dict[str, str],
    group_pair_targets: dict[tuple[str, str], float],
    seed: dict[tuple[str, str], float],
    max_iterations: int = 10000,
    tolerance: float = 1e-10,
) -> dict[tuple[str, str], float]:
    _check_targets(origins, destinations, origin_targets, destination_targets)
    values = {
        (origin, destination): max(0.0, float(seed.get((origin, destination), 0.0)))
        for origin in origins
        for destination in destinations
    }
    if abs(sum(group_pair_targets.values()) - sum(origin_targets)) > tolerance:
        raise InfeasibleConstraints("group-pair total differs from OD total")
    for _ in range(max_iterations):
        for origin, target in zip(origins, origin_targets):
            total = sum(values[(origin, destination)] for destination in destinations)
            if total == 0 and target == 0:
                continue
            if total == 0:
                raise InfeasibleConstraints(f"origin {origin} has no feasible destination")
            factor = target / total
            for destination in destinations:
                values[(origin, destination)] *= factor
        for destination, target in zip(destinations, destination_targets):
            total = sum(values[(origin, destination)] for origin in origins)
            if total == 0 and target == 0:
                continue
            if total == 0:
                raise InfeasibleConstraints(f"destination {destination} has no feasible origin")
            factor = target / total
            for origin in origins:
                values[(origin, destination)] *= factor
        for (origin_group, destination_group), target in sorted(group_pair_targets.items()):
            cells = [
                (origin, destination)
                for origin in origins
                for destination in destinations
                if origin_groups[origin] == origin_group
                and destination_groups[destination] == destination_group
            ]
            total = sum(values[cell] for cell in cells)
            if total == 0 and target == 0:
                continue
            if total == 0:
                raise InfeasibleConstraints(f"group pair {origin_group}/{destination_group} is structurally zero")
            factor = target / total
            for cell in cells:
                values[cell] *= factor
        errors = [
            abs(sum(values[(origin, destination)] for destination in destinations) - target)
            for origin, target in zip(origins, origin_targets)
        ]
        errors += [
            abs(sum(values[(origin, destination)] for origin in origins) - target)
            for destination, target in zip(destinations, destination_targets)
        ]
        errors += [
            abs(
                sum(
                    values[(origin, destination)]
                    for origin in origins
                    for destination in destinations
                    if origin_groups[origin] == origin_group
                    and destination_groups[destination] == destination_group
                )
                - target
            )
            for (origin_group, destination_group), target in sorted(group_pair_targets.items())
        ]
        if max(errors, default=0.0) <= tolerance:
            return values
    raise InfeasibleConstraints("constrained IPF did not converge")


@dataclass(frozen=True)
class ODRecord:
    origin: str
    destination: str
    demand: float
    purpose: str
    vehicle_class: str
    classification: str = "C"


def split_purposes(records: Iterable[ODRecord]) -> dict[str, list[ODRecord]]:
    result: dict[str, list[ODRecord]] = {}
    for record in records:
        result.setdefault(record.purpose, []).append(record)
    return result
