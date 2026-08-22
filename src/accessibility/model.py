"""Population-weighted accessibility summaries."""

from __future__ import annotations

from typing import Iterable


def reachable_population(
    population_zones: Iterable[dict[str, float]],
    travel_time_minutes: dict[str, float],
    thresholds: tuple[int, ...] = (30, 60, 90),
) -> dict[str, float]:
    zones = list(population_zones)
    total = sum(float(zone.get("population", 0.0)) for zone in zones)
    result: dict[str, float] = {"total_population": total}
    for threshold in thresholds:
        result[f"reachable_{threshold}_min"] = sum(
            float(zone.get("population", 0.0))
            for zone in zones
            if travel_time_minutes.get(str(zone["zone_id"]), float("inf")) <= threshold
        )
    return result


def accessibility_loss(
    baseline: dict[str, float],
    after: dict[str, float],
    thresholds: tuple[int, ...] = (30, 60, 90),
) -> dict[str, float]:
    result: dict[str, float] = {}
    for threshold in thresholds:
        key = f"reachable_{threshold}_min"
        base = float(baseline.get(key, 0.0))
        change = base - float(after.get(key, 0.0))
        result[f"loss_{threshold}_min"] = change
        result[f"loss_pct_{threshold}_min"] = change / base * 100.0 if base else 0.0
    return result
