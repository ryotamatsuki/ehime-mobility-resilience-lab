"""Execute deterministic model fixtures and save auditable validation outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from common.graph import DirectedGraph, Edge
from common.provenance import make_provenance
from od.synthetic import gravity_seed, ipf
from traffic.assignment import AssignmentParameters, assign_user_equilibrium
from validation.metrics import holdout_split, validation_summary


def build_od_fixture() -> dict[str, object]:
    origins = ["a", "b"]
    destinations = ["x", "y"]
    seed = gravity_seed(
        origins,
        destinations,
        [5, 3],
        [4, 4],
        {("a", "x"): 1, ("a", "y"): 2, ("b", "x"): 2, ("b", "y"): 1},
        beta=0.2,
    )
    matrix = ipf(origins, destinations, [5, 3], [4, 4], seed)
    return {
        "classification": "C",
        "origins": origins,
        "destinations": destinations,
        "matrix": {f"{origin}|{destination}": value for (origin, destination), value in matrix.items()},
        "row_totals": {
            origin: sum(matrix[(origin, destination)] for destination in destinations)
            for origin in origins
        },
        "column_totals": {
            destination: sum(matrix[(origin, destination)] for origin in origins)
            for destination in destinations
        },
        "total": sum(matrix.values()),
        "constraints": "fixture margins only; not Ehime observed OD",
    }


def build_traffic_fixture() -> dict[str, object]:
    graph = DirectedGraph()
    graph.add_edge(Edge("ab", "a", "b", 1.0, 60.0, 100.0))
    graph.add_edge(Edge("bc", "b", "c", 1.0, 60.0, 100.0))
    graph.add_edge(Edge("ac", "a", "c", 3.0, 60.0, 100.0))
    od = [("a", "c", 50.0)]
    baseline = assign_user_equilibrium(graph, od, AssignmentParameters(iterations=25))
    after = assign_user_equilibrium(graph, od, AssignmentParameters(iterations=25), {"bc"})
    observed = {"ab": 45.0, "bc": 45.0, "ac": 5.0}
    metrics = validation_summary(
        baseline.volumes,
        observed,
        {edge_id: edge.length_km for edge_id, edge in graph.edges.items()},
    )
    calibration, validation = holdout_split(observed, calibration_percent=80)
    return {
        "classification": "C",
        "baseline_volumes": baseline.volumes,
        "closure_volumes": after.volumes,
        "closure_unreachable_demand": after.unreachable_demand,
        "parameters": {
            "alpha": 0.15,
            "beta": 4.0,
            "iterations": 25,
            "method": "deterministic MSA approximation",
        },
        "validation_fixture": {
            "observed": observed,
            "calibration_ids": calibration,
            "holdout_ids": validation,
            "metrics": metrics,
        },
        "limitations": ["Synthetic fixture only; not a calibration result for Ehime."],
    }


def main() -> None:
    output = ROOT / "outputs" / "fixtures"
    output.mkdir(parents=True, exist_ok=True)
    provenance = make_provenance(
        "deterministic-model-fixtures",
        "C",
        "model-fixture-v0.1.0",
        [],
        {"seed": 0, "ordering": "lexicographic"},
        limitations=["Fixture results are not official Ehime measurements."],
        repository=ROOT,
        random_seed=0,
    )
    payload = {
        "provenance": provenance,
        "od": build_od_fixture(),
        "traffic": build_traffic_fixture(),
    }
    (output / "model_validation.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output / "model_validation.json"), "status": "passed"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
