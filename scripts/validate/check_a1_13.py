"""Validate the machine-readable A1.13 robustness result contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_CASES = [
    "baseline",
    "walk_speed_3_6",
    "walk_speed_1_8",
    "access_walk_10",
    "access_walk_30",
    "transfer_walk_5",
    "transfer_walk_15",
]
DESTINATIONS = ("hospital", "emergency", "general", "welfare")
GROUPS = ("65plus", "75plus", "85plus")
METRICS = ("affected_share_gt1min_gap_pp", "mean_minutes_change_gap")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(output: Path) -> dict[str, Any]:
    summary = read_json(output / "summary.json")
    robustness = read_json(output / "robustness_summary.json")
    cases = read_json(output / "robustness_cases.json")
    predecessor_summary = read_json(output / "a1_12" / "summary.json")

    if summary.get("stage") != "A1.13" or robustness.get("stage") != "A1.13":
        raise AssertionError("A1.13 stage contract invalid")
    if predecessor_summary.get("stage") != "A1.12":
        raise AssertionError("A1.13 predecessor must remain A1.12")
    if robustness.get("composite_score") is not False:
        raise AssertionError("A1.13 must not create a composite robustness score")
    if robustness.get("case_count") != 7:
        raise AssertionError("A1.13 must execute seven pre-registered cases")
    if robustness.get("slots_per_case") != 16 or robustness.get("case_slot_combinations") != 112:
        raise AssertionError("A1.13 time/case coverage incomplete")
    if robustness.get("case_ids") != EXPECTED_CASES:
        raise AssertionError("A1.13 case registry changed")
    if [item.get("id") for item in cases.get("case_registry") or []] != EXPECTED_CASES:
        raise AssertionError("A1.13 cases payload registry changed")
    if set((cases.get("cases") or {}).keys()) != set(EXPECTED_CASES):
        raise AssertionError("A1.13 not all sensitivity cases were executed")
    if robustness.get("baseline_equivalence", {}).get("status") != "PASS":
        raise AssertionError("A1.13 baseline does not reproduce A1.11/A1.12")

    for case_id in EXPECTED_CASES:
        result = cases["cases"][case_id]
        diagnostics = result.get("diagnostics") or {}
        if diagnostics.get("slots") != 16:
            raise AssertionError(f"{case_id}: expected 16 slots")
        if diagnostics.get("route_evaluations", 0) <= 0 or diagnostics.get("trip_evaluations", 0) <= 0:
            raise AssertionError(f"{case_id}: leave-one-out evaluations missing")
        if not result.get("route_day_ranking") or not result.get("trip_day_ranking"):
            raise AssertionError(f"{case_id}: day ranking missing")
        if len(result.get("hourly_top") or []) != 16:
            raise AssertionError(f"{case_id}: hourly top coverage missing")
        if set((result.get("equity") or {}).keys()) != set(DESTINATIONS):
            raise AssertionError(f"{case_id}: equity destinations incomplete")

    for key in ("route_stability", "trip_stability"):
        item = robustness[key]
        if item.get("case_count") != 7 or len(item.get("per_case") or []) != 7:
            raise AssertionError(f"{key}: stability coverage incomplete")
        if not item.get("reference_id"):
            raise AssertionError(f"{key}: reference candidate missing")
        top1 = int(item.get("top1_count", -1))
        top3 = int(item.get("top3_count", -1))
        if not (0 <= top1 <= top3 <= 7):
            raise AssertionError(f"{key}: invalid preservation counts")

    equity = robustness.get("equity_direction_stability") or {}
    for destination in DESTINATIONS:
        for group in GROUPS:
            for metric in METRICS:
                item = equity[destination][group][metric]
                if item.get("case_count") != 7 or len(item.get("per_case") or []) != 7:
                    raise AssertionError(
                        f"equity stability incomplete: {destination}.{group}.{metric}"
                    )
                total = sum(
                    int(item.get(name, 0))
                    for name in (
                        "positive_count",
                        "neutral_count",
                        "negative_count",
                        "unknown_count",
                    )
                )
                if total != 7:
                    raise AssertionError(
                        f"equity direction counts invalid: {destination}.{group}.{metric}"
                    )

    result = {
        "status": "PASS",
        "case_count": 7,
        "slots_per_case": 16,
        "case_slot_combinations": 112,
        "reference_route_id": robustness["route_stability"]["reference_id"],
        "reference_trip_id": robustness["trip_stability"]["reference_id"],
        "boundary_case_ids": robustness["boundary_conditions"]["case_ids"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "a1_13")
    args = parser.parse_args()
    validate(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
