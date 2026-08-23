"""Traffic validation metrics with explicit zero handling."""

from __future__ import annotations

import math
from collections.abc import Iterable


def geh(model: float, observed: float) -> float:
    denominator = model + observed
    if denominator == 0:
        return 0.0
    return math.sqrt(2.0 * (model - observed) ** 2 / denominator)


def mape(model: Iterable[float], observed: Iterable[float], minimum_observed: float = 0.0) -> float:
    pairs = [
        (float(m), float(o))
        for m, o in zip(model, observed, strict=True)
        if abs(float(o)) > minimum_observed
    ]
    if not pairs:
        return float("nan")
    return sum(abs(m - o) / abs(o) for m, o in pairs) / len(pairs) * 100.0


def rmse(model: Iterable[float], observed: Iterable[float]) -> float:
    pairs = [(float(m), float(o)) for m, o in zip(model, observed, strict=True)]
    if not pairs:
        return float("nan")
    return math.sqrt(sum((m - o) ** 2 for m, o in pairs) / len(pairs))


def wape(model: Iterable[float], observed: Iterable[float]) -> float:
    pairs = [(float(m), float(o)) for m, o in zip(model, observed, strict=True)]
    denominator = sum(abs(o) for _, o in pairs)
    if denominator == 0:
        return float("nan")
    return sum(abs(m - o) for m, o in pairs) / denominator * 100.0


def screenline(model: dict[str, float], observed: dict[str, float], edge_ids: Iterable[str]) -> dict[str, float]:
    selected = list(edge_ids)
    model_total = sum(model.get(edge_id, 0.0) for edge_id in selected)
    observed_total = sum(observed.get(edge_id, 0.0) for edge_id in selected)
    error_pct = float("nan") if observed_total == 0 else (model_total - observed_total) / observed_total * 100.0
    return {
        "model": model_total,
        "observed": observed_total,
        "error_pct": error_pct,
        "edge_count": float(len(selected)),
    }


def vkt(volumes: dict[str, float], lengths_km: dict[str, float]) -> float:
    return sum(float(volumes.get(edge_id, 0.0)) * float(lengths_km.get(edge_id, 0.0)) for edge_id in volumes)


def holdout_split(ids: Iterable[str], calibration_percent: int = 80) -> tuple[list[str], list[str]]:
    if not 0 < calibration_percent < 100:
        raise ValueError("calibration_percent must be between 0 and 100")
    calibration: list[str] = []
    validation: list[str] = []
    for identifier in sorted(set(ids)):
        bucket = int.from_bytes(identifier.encode("utf-8"), "little", signed=False) % 100
        if bucket < calibration_percent:
            calibration.append(identifier)
        else:
            validation.append(identifier)
    return calibration, validation


def validation_summary(
    model: dict[str, float],
    observed: dict[str, float],
    lengths_km: dict[str, float],
) -> dict[str, float | int]:
    common = sorted(set(model) & set(observed))
    model_values = [model[edge_id] for edge_id in common]
    observed_values = [observed[edge_id] for edge_id in common]
    return {
        "link_count": len(common),
        "geh_lt_5_share": (
            sum(geh(m, o) < 5 for m, o in zip(model_values, observed_values, strict=True)) / len(common) * 100
            if common
            else float("nan")
        ),
        "mape_pct": mape(model_values, observed_values),
        "wape_pct": wape(model_values, observed_values),
        "rmse": rmse(model_values, observed_values),
        "model_vkt": vkt(model, lengths_km),
        "observed_vkt": vkt(observed, lengths_km),
    }