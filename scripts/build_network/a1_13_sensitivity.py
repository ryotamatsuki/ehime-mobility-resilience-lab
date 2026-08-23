"""Pure helpers for A1.13 robustness and uncertainty analysis."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

BASE_WALK_SPEED_KMH = 4.8
DIRECTION_EPSILON = 0.0005


@dataclass(frozen=True)
class SensitivityCase:
    id: str
    label: str
    walk_speed_kmh: float
    max_access_walk_minutes: float
    max_transfer_walk_minutes: float
    varied_parameter: str | None
    varied_value: float | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


SENSITIVITY_CASES: tuple[SensitivityCase, ...] = (
    SensitivityCase(
        "baseline",
        "基準",
        4.8,
        20.0,
        10.0,
        None,
        None,
    ),
    SensitivityCase(
        "walk_speed_3_6",
        "歩行速度 3.6 km/h (1.0 m/s)",
        3.6,
        20.0,
        10.0,
        "walk_speed_kmh",
        3.6,
    ),
    SensitivityCase(
        "walk_speed_1_8",
        "歩行速度 1.8 km/h (0.5 m/s)",
        1.8,
        20.0,
        10.0,
        "walk_speed_kmh",
        1.8,
    ),
    SensitivityCase(
        "access_walk_10",
        "アクセス徒歩上限 10分",
        4.8,
        10.0,
        10.0,
        "max_access_walk_minutes",
        10.0,
    ),
    SensitivityCase(
        "access_walk_30",
        "アクセス徒歩上限 30分",
        4.8,
        30.0,
        10.0,
        "max_access_walk_minutes",
        30.0,
    ),
    SensitivityCase(
        "transfer_walk_5",
        "乗換徒歩上限 5分",
        4.8,
        20.0,
        5.0,
        "max_transfer_walk_minutes",
        5.0,
    ),
    SensitivityCase(
        "transfer_walk_15",
        "乗換徒歩上限 15分",
        4.8,
        20.0,
        15.0,
        "max_transfer_walk_minutes",
        15.0,
    ),
)


def validate_cases(cases: tuple[SensitivityCase, ...] = SENSITIVITY_CASES) -> None:
    ids = [case.id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("A1.13 sensitivity case IDs must be unique")
    if not cases or cases[0].id != "baseline":
        raise ValueError("A1.13 first sensitivity case must be baseline")
    baseline = cases[0]
    if (
        baseline.walk_speed_kmh != BASE_WALK_SPEED_KMH
        or baseline.max_access_walk_minutes != 20.0
        or baseline.max_transfer_walk_minutes != 10.0
        or baseline.varied_parameter is not None
    ):
        raise ValueError("A1.13 baseline contract changed")
    for case in cases:
        if case.walk_speed_kmh <= 0:
            raise ValueError(f"{case.id}: walk speed must be positive")
        if case.max_access_walk_minutes < 0 or case.max_transfer_walk_minutes < 0:
            raise ValueError(f"{case.id}: walk limits must be non-negative")


def scale_minutes(value: float, walk_speed_kmh: float) -> float:
    """Scale a baseline 4.8 km/h network travel time to a uniform walk speed."""
    if walk_speed_kmh <= 0:
        raise ValueError("walk speed must be positive")
    return float(value) * BASE_WALK_SPEED_KMH / float(walk_speed_kmh)


def scale_minute_map(values: dict[str, float], walk_speed_kmh: float) -> dict[str, float]:
    return {key: scale_minutes(value, walk_speed_kmh) for key, value in values.items()}


def scale_nested_minute_map(
    values: dict[str, dict[str, float]], walk_speed_kmh: float
) -> dict[str, dict[str, float]]:
    return {
        outer: scale_minute_map(inner, walk_speed_kmh)
        for outer, inner in values.items()
    }


def ranking_key(item: dict[str, Any]) -> tuple[float, float, str]:
    impact = item["impact"]
    return (
        -float(impact["population_with_gt_1min_increase"]),
        -float(impact["mean_minutes_change"]),
        str(item["id"]),
    )


def aggregate_candidate_ranking(
    rows: list[dict[str, Any]], ranking_field: str
) -> list[dict[str, Any]]:
    """Rank candidates by their worst observed material event across all slots."""
    best_by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        for item in row[ranking_field]:
            if not item.get("evaluated"):
                continue
            candidate = {
                **item,
                "peak_departure_time": row["departure_time"],
                "peak_departure_seconds": row["departure_seconds"],
            }
            current = best_by_id.get(str(item["id"]))
            if current is None:
                best_by_id[str(item["id"])] = candidate
                continue
            candidate_key = (
                float(candidate["impact"]["population_with_gt_1min_increase"]),
                float(candidate["impact"]["mean_minutes_change"]),
                -int(candidate["peak_departure_seconds"]),
            )
            current_key = (
                float(current["impact"]["population_with_gt_1min_increase"]),
                float(current["impact"]["mean_minutes_change"]),
                -int(current["peak_departure_seconds"]),
            )
            if candidate_key > current_key:
                best_by_id[str(item["id"])] = candidate

    ranking = list(best_by_id.values())
    ranking.sort(key=ranking_key)
    for rank, item in enumerate(ranking, 1):
        item["rank"] = rank
    return ranking


def reference_stability(
    case_rankings: dict[str, list[dict[str, Any]]],
    *,
    reference_case_id: str = "baseline",
    top_k: int = 3,
) -> dict[str, Any]:
    if reference_case_id not in case_rankings:
        raise ValueError("reference sensitivity case missing")
    reference = case_rankings[reference_case_id]
    if not reference:
        raise ValueError("reference ranking is empty")
    reference_item = reference[0]
    reference_id = str(reference_item["id"])
    per_case: list[dict[str, Any]] = []
    top1_count = 0
    topk_count = 0
    for case_id, ranking in case_rankings.items():
        found = next((item for item in ranking if str(item["id"]) == reference_id), None)
        rank = None if found is None else int(found["rank"])
        if rank == 1:
            top1_count += 1
        if rank is not None and rank <= top_k:
            topk_count += 1
        per_case.append(
            {
                "case_id": case_id,
                "rank": rank,
                "peak_departure_time": None if found is None else found.get("peak_departure_time"),
                "impact": None if found is None else found.get("impact"),
            }
        )
    return {
        "reference_case_id": reference_case_id,
        "reference_id": reference_id,
        "reference_label": reference_item.get("route_name")
        or reference_item.get("trip_headsign")
        or reference_id,
        "case_count": len(case_rankings),
        "top1_count": top1_count,
        "top3_count": topk_count if top_k == 3 else None,
        "top_k": top_k,
        "top_k_count": topk_count,
        "per_case": per_case,
        "changed_top1_cases": [item["case_id"] for item in per_case if item["rank"] != 1],
        "outside_top_k_cases": [
            item["case_id"]
            for item in per_case
            if item["rank"] is None or int(item["rank"]) > top_k
        ],
    }


def direction(value: float | None, epsilon: float = DIRECTION_EPSILON) -> str:
    if value is None:
        return "unknown"
    number = float(value)
    if number > epsilon:
        return "positive"
    if number < -epsilon:
        return "negative"
    return "neutral"


def direction_stability(
    case_values: dict[str, float | None],
    *,
    reference_case_id: str = "baseline",
) -> dict[str, Any]:
    if reference_case_id not in case_values:
        raise ValueError("reference sensitivity case missing")
    reference_value = case_values[reference_case_id]
    reference_direction = direction(reference_value)
    per_case = [
        {
            "case_id": case_id,
            "value": value,
            "direction": direction(value),
            "matches_reference": direction(value) == reference_direction,
        }
        for case_id, value in case_values.items()
    ]
    return {
        "reference_case_id": reference_case_id,
        "reference_value": reference_value,
        "reference_direction": reference_direction,
        "case_count": len(case_values),
        "same_direction_count": sum(1 for item in per_case if item["matches_reference"]),
        "changed_direction_cases": [item["case_id"] for item in per_case if not item["matches_reference"]],
        "positive_count": sum(1 for item in per_case if item["direction"] == "positive"),
        "neutral_count": sum(1 for item in per_case if item["direction"] == "neutral"),
        "negative_count": sum(1 for item in per_case if item["direction"] == "negative"),
        "unknown_count": sum(1 for item in per_case if item["direction"] == "unknown"),
        "per_case": per_case,
    }
