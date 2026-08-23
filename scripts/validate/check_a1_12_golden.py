"""Fail when an A1.12 hardening change alters the verified public result contract.

The snapshot is intentionally small: it protects the externally visible A1.12
population/equity results that were verified on main before refactoring, while
leaving implementation details free to change. Updating the snapshot requires
an explicit review of the underlying public-data change or model change.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "outputs" / "a1_12"
DEFAULT_GOLDEN = ROOT / "tests" / "fixtures" / "a1_12_golden.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_close(label: str, actual: Any, expected: Any, tolerance: float = 1e-6) -> None:
    if actual is None or expected is None:
        if actual != expected:
            raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
        return
    if abs(float(actual) - float(expected)) > tolerance:
        raise AssertionError(f"{label}: expected {expected}, got {actual}")


def validate(output: Path, golden_path: Path) -> None:
    golden = read_json(golden_path)
    summary = read_json(output / "summary.json")
    equity = read_json(output / "equity_summary.json")
    geo = read_json(output / "vulnerable_population_access.geojson")

    if summary.get("stage") != "A1.12" or equity.get("stage") != "A1.12":
        raise AssertionError("A1.12 stage contract changed")
    if equity.get("interpretation", {}).get("composite_score") is not False:
        raise AssertionError("A1.12 must not introduce a composite vulnerability score")

    expected_zones = int(golden["analysis_zones"])
    actual_zones = int(summary.get("population", {}).get("zones_in_envelope", -1))
    feature_count = len(geo.get("features") or [])
    if actual_zones != expected_zones or feature_count != expected_zones:
        raise AssertionError(
            f"analysis zones changed: summary={actual_zones}, geojson={feature_count}, expected={expected_zones}"
        )

    totals = summary.get("vulnerable_population", {}).get("group_totals_in_analysis_envelope", {})
    for group, expected in golden["mesh_group_totals"].items():
        assert_close(f"mesh_group_totals.{group}", totals.get(group), expected, 1e-4)

    current = equity.get("population_sources", {}).get("current_official_context", {})
    for key, expected in golden["current_official_context"].items():
        assert_close(f"current_official_context.{key}", current.get(key), expected, 1e-3)

    destinations = equity.get("destinations", {})
    for destination, expected_groups in golden["destinations"].items():
        actual_groups = destinations.get(destination, {}).get("groups", {})
        for group, expected_metrics in expected_groups.items():
            actual_metrics = actual_groups.get(group, {})
            for metric, expected in expected_metrics.items():
                tolerance = 1e-4 if metric == "affected_gt1min" else 1e-3
                assert_close(
                    f"destinations.{destination}.{group}.{metric}",
                    actual_metrics.get(metric),
                    expected,
                    tolerance,
                )

    print(
        json.dumps(
            {
                "status": "PASS",
                "reference_main_sha": golden["reference_main_sha"],
                "analysis_zones": expected_zones,
                "destinations_checked": sorted(golden["destinations"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    args = parser.parse_args()
    validate(args.output, args.golden)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
