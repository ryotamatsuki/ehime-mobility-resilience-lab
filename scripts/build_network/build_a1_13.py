"""A1.13: deterministic robustness / uncertainty analysis for the Ozu A1 model.

A1.12 is generated into a protected predecessor subdirectory and remains
Golden-checkable. Seven pre-registered sensitivity cases then rerun the same
hospital route/trip leave-one-out analysis across all 16 hourly slots and the
same 08:00 clockwise-route equity analysis across all four destination classes.

A1.13 reports condition preservation counts and boundary cases directly. It
never creates a composite robustness score or interprets sensitivity cases as
failure probabilities or confidence intervals.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from accessibility.equity import AGE_GROUP_FIELDS, equity_gaps, group_access_metrics
from accessibility.multimodal import (
    CoordinateIndex,
    earliest_arrival_minutes,
    min_walk_minutes_to_facility,
    stop_transfer_edges,
    stop_walk_times,
    summarize_population_access,
    walking_graph_from_overpass,
)
from common.provenance import make_provenance
from scripts.build_network.a1_13_sensitivity import (
    SENSITIVITY_CASES,
    aggregate_candidate_ranking,
    direction_stability,
    ranking_key,
    reference_stability,
    scale_minute_map,
    scale_nested_minute_map,
    validate_cases,
)
from scripts.build_network.build_a1_1 import (
    ANALYSIS_DATE,
    GTFS_LANDING,
    GTFS_URL,
    POP_LANDING,
    POP_URL,
    fetch,
    fetch_osm,
    first_csv_rows,
    gtfs_bbox,
    load_feed,
    population_zones,
    snap_points,
    zones_to_nodes,
)
from scripts.build_network.build_a1_6 import TRANSFER_BUFFER_MINUTES
from scripts.build_network.build_a1_7 import (
    REFERENCE_DEPARTURE_SECONDS,
    TEMPORAL_END_HOUR,
    TEMPORAL_START_HOUR,
    TEMPORAL_STEP_MINUTES,
    impact_metrics,
    time_label,
)
from scripts.build_network.build_a1_12 import (
    DESTINATION_SPECS,
    build as build_a1_12,
)

THRESHOLDS = (30, 45, 60, 90)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _finite_or_none(value: float) -> float | None:
    """Match the two-decimal zone-minute precision consumed by A1.12 equity."""
    return round(float(value), 2) if math.isfinite(float(value)) else None


def _point_records(path: Path, *, kind: str | None = None) -> list[dict[str, Any]]:
    payload = read_json(path)
    if payload.get("type") != "FeatureCollection":
        raise ValueError(f"invalid point GeoJSON: {path}")
    records: list[dict[str, Any]] = []
    for feature in payload.get("features") or []:
        props = feature.get("properties") or {}
        if kind is not None and str(props.get("kind")) != kind:
            continue
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if geometry.get("type") != "Point" or len(coordinates) < 2:
            continue
        record_id = str(feature.get("id") or props.get("shelter_id") or props.get("name") or "")
        if not record_id:
            continue
        records.append(
            {
                "id": record_id,
                "name": str(props.get("name") or record_id),
                "lat": float(coordinates[1]),
                "lon": float(coordinates[0]),
            }
        )
    return records


def _evaluate(
    *,
    departure_seconds: int,
    zones: list[dict[str, Any]],
    connections: list[dict[str, Any]],
    trip_routes: dict[str, str],
    stop_walk: dict[str, dict[str, float]],
    facility_walk_by_node: dict[str, float],
    stop_nodes: dict[str, str],
    transfers: dict[str, list[dict[str, float | str]]],
    max_access_walk_minutes: float,
    disabled_routes: set[str] | None = None,
    disabled_trips: set[str] | None = None,
) -> tuple[dict[str, float], dict[str, float]]:
    values: dict[str, float] = {}
    for zone in zones:
        zone_id = str(zone["zone_id"])
        values[zone_id] = earliest_arrival_minutes(
            zone_node=str(zone["node"]),
            departure_seconds=departure_seconds,
            connections=connections,
            trip_routes=trip_routes,
            stop_walk=stop_walk,
            facility_walk_by_node=facility_walk_by_node,
            stop_nodes=stop_nodes,
            disabled_routes=disabled_routes or set(),
            disabled_trips=disabled_trips or set(),
            max_access_walk_minutes=max_access_walk_minutes,
            stop_transfers=transfers,
        )
    return values, summarize_population_access(zones, values)


def _assert_outage_monotonic(
    baseline_minutes: dict[str, float], outage_minutes: dict[str, float], label: str
) -> None:
    for zone_id, before in baseline_minutes.items():
        after = outage_minutes.get(zone_id, math.inf)
        if math.isfinite(before) and math.isfinite(after) and after + 1e-6 < before:
            raise ValueError(f"{label} unexpectedly improves zone {zone_id}")
        if not math.isfinite(before) and math.isfinite(after):
            raise ValueError(f"{label} unexpectedly makes unreachable zone {zone_id} reachable")


def _zero_impact() -> dict[str, Any]:
    return {
        "population_with_gt_1min_increase": 0.0,
        "population_with_gt_5min_increase": 0.0,
        "population_with_gt_10min_increase": 0.0,
        "accessibility_loss_30min_population": 0.0,
        "accessibility_loss_60min_population": 0.0,
        "mean_minutes_change": 0.0,
        "threshold_losses": {str(threshold): 0.0 for threshold in THRESHOLDS},
    }


def _threshold_losses(
    zones: list[dict[str, Any]],
    baseline_minutes: dict[str, float],
    disrupted_minutes: dict[str, float],
) -> dict[str, float]:
    result: dict[str, float] = {}
    for threshold in THRESHOLDS:
        before = sum(
            float(zone["population"])
            for zone in zones
            if baseline_minutes.get(str(zone["zone_id"]), math.inf) <= threshold
        )
        after = sum(
            float(zone["population"])
            for zone in zones
            if disrupted_minutes.get(str(zone["zone_id"]), math.inf) <= threshold
        )
        result[str(threshold)] = round(before - after, 4)
    return result


def _impact(
    zones: list[dict[str, Any]],
    baseline_minutes: dict[str, float],
    disrupted_minutes: dict[str, float],
    baseline: dict[str, float],
    disrupted: dict[str, float],
) -> dict[str, Any]:
    result: dict[str, Any] = impact_metrics(
        zones, baseline_minutes, disrupted_minutes, baseline, disrupted
    )
    result["threshold_losses"] = _threshold_losses(zones, baseline_minutes, disrupted_minutes)
    return result


def _material(impact: dict[str, Any]) -> bool:
    return any(
        float(impact.get(key, 0.0) or 0.0) > 1e-6
        for key in (
            "population_with_gt_1min_increase",
            "accessibility_loss_30min_population",
            "accessibility_loss_60min_population",
            "mean_minutes_change",
        )
    )


def _first_material(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((item for item in items if _material(item["impact"])), None)


def _remaining_candidates(
    connections: list[dict[str, Any]], departure_seconds: int
) -> tuple[set[str], int]:
    future = [
        connection
        for connection in connections
        if int(connection["departure_seconds"]) >= departure_seconds
    ]
    return {str(connection["trip_id"]) for connection in future}, len(future)


def _age_weights(predecessor: Path) -> dict[str, dict[str, float]]:
    payload = read_json(predecessor / "vulnerable_population_access.geojson")
    result: dict[str, dict[str, float]] = {}
    for feature in payload.get("features") or []:
        props = feature.get("properties") or {}
        zone_id = str(props.get("zone_id") or feature.get("id") or "")
        if not zone_id:
            continue
        result[zone_id] = {
            field: float(props.get(field) or 0.0)
            for field in AGE_GROUP_FIELDS.values()
        }
    if not result:
        raise ValueError("A1.13 has no predecessor age weights")
    return result


def _equity_features(
    zones: list[dict[str, Any]],
    age_by_zone: dict[str, dict[str, float]],
    baseline_minutes: dict[str, float],
    disrupted_minutes: dict[str, float],
) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    for zone in zones:
        zone_id = str(zone["zone_id"])
        weights = age_by_zone.get(zone_id)
        if weights is None:
            raise ValueError(f"A1.13 missing age weights for zone {zone_id}")
        props = dict(weights)
        props["baseline"] = _finite_or_none(baseline_minutes.get(zone_id, math.inf))
        props["disrupted"] = _finite_or_none(disrupted_minutes.get(zone_id, math.inf))
        features.append({"type": "Feature", "properties": props})
    return features


def _build_case(
    *,
    case,
    zones: list[dict[str, Any]],
    connections: list[dict[str, Any]],
    trip_routes: dict[str, str],
    trip_rows: dict[str, dict[str, str]],
    route_names: dict[str, str],
    all_route_ids: list[str],
    all_trip_ids: list[str],
    first_departure: dict[str, int],
    stop_nodes: dict[str, str],
    base_stop_walk: dict[str, dict[str, float]],
    base_facility_walk: dict[str, dict[str, float]],
    right_loop_routes: set[str],
    age_by_zone: dict[str, dict[str, float]],
) -> dict[str, Any]:
    stop_walk = scale_nested_minute_map(base_stop_walk, case.walk_speed_kmh)
    transfers = stop_transfer_edges(
        stop_walk,
        stop_nodes,
        max_walk_minutes=case.max_transfer_walk_minutes,
        transfer_buffer_minutes=TRANSFER_BUFFER_MINUTES,
    )
    hospital_walk = scale_minute_map(base_facility_walk["hospital"], case.walk_speed_kmh)

    rows: list[dict[str, Any]] = []
    route_evaluations = 0
    trip_evaluations = 0
    step_seconds = TEMPORAL_STEP_MINUTES * 60
    for departure_seconds in range(
        TEMPORAL_START_HOUR * 3600,
        TEMPORAL_END_HOUR * 3600 + 1,
        step_seconds,
    ):
        label = time_label(departure_seconds)
        baseline_minutes, baseline = _evaluate(
            departure_seconds=departure_seconds,
            zones=zones,
            connections=connections,
            trip_routes=trip_routes,
            stop_walk=stop_walk,
            facility_walk_by_node=hospital_walk,
            stop_nodes=stop_nodes,
            transfers=transfers,
            max_access_walk_minutes=case.max_access_walk_minutes,
        )
        future_trip_ids, remaining_connections = _remaining_candidates(
            connections, departure_seconds
        )
        future_route_ids = {trip_routes[trip_id] for trip_id in future_trip_ids}

        route_ranking: list[dict[str, Any]] = []
        for route_id in all_route_ids:
            if route_id not in future_route_ids:
                route_ranking.append(
                    {
                        "id": route_id,
                        "route_name": route_names.get(route_id, route_id),
                        "evaluated": False,
                        "skip_reason": "no_remaining_boardable_connection",
                        "impact": _zero_impact(),
                    }
                )
                continue
            outage_minutes, outage = _evaluate(
                departure_seconds=departure_seconds,
                zones=zones,
                connections=connections,
                trip_routes=trip_routes,
                stop_walk=stop_walk,
                facility_walk_by_node=hospital_walk,
                stop_nodes=stop_nodes,
                transfers=transfers,
                max_access_walk_minutes=case.max_access_walk_minutes,
                disabled_routes={route_id},
            )
            _assert_outage_monotonic(
                baseline_minutes, outage_minutes, f"{case.id}:{label}:route:{route_id}"
            )
            route_evaluations += 1
            route_ranking.append(
                {
                    "id": route_id,
                    "route_name": route_names.get(route_id, route_id),
                    "evaluated": True,
                    "impact": _impact(
                        zones, baseline_minutes, outage_minutes, baseline, outage
                    ),
                }
            )
        route_ranking.sort(key=ranking_key)
        for rank, item in enumerate(route_ranking, 1):
            item["rank"] = rank

        trip_ranking: list[dict[str, Any]] = []
        for trip_id in all_trip_ids:
            trip_row = trip_rows[trip_id]
            common = {
                "id": trip_id,
                "route_id": trip_routes[trip_id],
                "route_name": route_names.get(trip_routes[trip_id], trip_routes[trip_id]),
                "trip_headsign": trip_row.get("trip_headsign") or "",
                "first_departure": time_label(first_departure[trip_id]),
            }
            if trip_id not in future_trip_ids:
                trip_ranking.append(
                    {
                        **common,
                        "evaluated": False,
                        "skip_reason": "no_remaining_boardable_connection",
                        "impact": _zero_impact(),
                    }
                )
                continue
            outage_minutes, outage = _evaluate(
                departure_seconds=departure_seconds,
                zones=zones,
                connections=connections,
                trip_routes=trip_routes,
                stop_walk=stop_walk,
                facility_walk_by_node=hospital_walk,
                stop_nodes=stop_nodes,
                transfers=transfers,
                max_access_walk_minutes=case.max_access_walk_minutes,
                disabled_trips={trip_id},
            )
            _assert_outage_monotonic(
                baseline_minutes, outage_minutes, f"{case.id}:{label}:trip:{trip_id}"
            )
            trip_evaluations += 1
            trip_ranking.append(
                {
                    **common,
                    "evaluated": True,
                    "impact": _impact(
                        zones, baseline_minutes, outage_minutes, baseline, outage
                    ),
                }
            )
        trip_ranking.sort(key=ranking_key)
        for rank, item in enumerate(trip_ranking, 1):
            item["rank"] = rank

        rows.append(
            {
                "departure_time": label,
                "departure_seconds": departure_seconds,
                "remaining_boardable_connections": remaining_connections,
                "route_ranking": route_ranking,
                "trip_ranking": trip_ranking,
            }
        )

    route_day_ranking = aggregate_candidate_ranking(rows, "route_ranking")
    trip_day_ranking = aggregate_candidate_ranking(rows, "trip_ranking")
    hourly_top = [
        {
            "departure_time": row["departure_time"],
            "top_route": _first_material(row["route_ranking"]),
            "top_trip": _first_material(row["trip_ranking"]),
        }
        for row in rows
    ]

    equity: dict[str, Any] = {}
    for destination, (_, _, _) in DESTINATION_SPECS.items():
        facility_walk = scale_minute_map(
            base_facility_walk[destination], case.walk_speed_kmh
        )
        baseline_minutes, _ = _evaluate(
            departure_seconds=REFERENCE_DEPARTURE_SECONDS,
            zones=zones,
            connections=connections,
            trip_routes=trip_routes,
            stop_walk=stop_walk,
            facility_walk_by_node=facility_walk,
            stop_nodes=stop_nodes,
            transfers=transfers,
            max_access_walk_minutes=case.max_access_walk_minutes,
        )
        disrupted_minutes, _ = _evaluate(
            departure_seconds=REFERENCE_DEPARTURE_SECONDS,
            zones=zones,
            connections=connections,
            trip_routes=trip_routes,
            stop_walk=stop_walk,
            facility_walk_by_node=facility_walk,
            stop_nodes=stop_nodes,
            transfers=transfers,
            max_access_walk_minutes=case.max_access_walk_minutes,
            disabled_routes=right_loop_routes,
        )
        features = _equity_features(
            zones, age_by_zone, baseline_minutes, disrupted_minutes
        )
        groups = {
            group: group_access_metrics(
                features,
                weight_key=weight_field,
                baseline_key="baseline",
                disrupted_key="disrupted",
            )
            for group, weight_field in AGE_GROUP_FIELDS.items()
        }
        equity[destination] = {
            "groups": groups,
            "gaps_vs_all": equity_gaps(groups),
        }

    return {
        "case": case.as_dict(),
        "diagnostics": {
            "slots": len(rows),
            "route_evaluations": route_evaluations,
            "trip_evaluations": trip_evaluations,
            "transfer_origin_stops": len(transfers),
        },
        "route_day_ranking": route_day_ranking,
        "trip_day_ranking": trip_day_ranking,
        "hourly_top": hourly_top,
        "equity": equity,
    }


def _assert_close(label: str, actual: Any, expected: Any, tolerance: float = 1e-3) -> None:
    if actual is None or expected is None:
        if actual != expected:
            raise ValueError(f"{label}: expected {expected!r}, got {actual!r}")
        return
    if abs(float(actual) - float(expected)) > tolerance:
        raise ValueError(f"{label}: expected {expected}, got {actual}")


def _verify_baseline_equivalence(
    baseline_case: dict[str, Any], predecessor: Path
) -> dict[str, Any]:
    td = read_json(predecessor / "time_dependent_criticality.json")
    equity = read_json(predecessor / "equity_summary.json")
    expected_peak_route = td["time_window"]["peak_route_event"]
    expected_peak_trip = td["time_window"]["peak_trip_event"]
    actual_route = baseline_case["route_day_ranking"][0]
    actual_trip = baseline_case["trip_day_ranking"][0]
    if str(actual_route["id"]) != str(expected_peak_route["id"]):
        raise ValueError("A1.13 baseline route identity diverges from A1.11")
    if actual_route["peak_departure_time"] != expected_peak_route["departure_time"]:
        raise ValueError("A1.13 baseline route peak time diverges from A1.11")
    if str(actual_trip["id"]) != str(expected_peak_trip["id"]):
        raise ValueError("A1.13 baseline trip identity diverges from A1.11")
    if actual_trip["peak_departure_time"] != expected_peak_trip["departure_time"]:
        raise ValueError("A1.13 baseline trip peak time diverges from A1.11")
    for metric in (
        "population_with_gt_1min_increase",
        "mean_minutes_change",
    ):
        _assert_close(
            f"baseline route {metric}",
            actual_route["impact"][metric],
            expected_peak_route["impact"][metric],
        )
        _assert_close(
            f"baseline trip {metric}",
            actual_trip["impact"][metric],
            expected_peak_trip["impact"][metric],
        )

    checked_equity = 0
    for destination in DESTINATION_SPECS:
        expected_destination = equity["destinations"][destination]
        actual_destination = baseline_case["equity"][destination]
        for group in AGE_GROUP_FIELDS:
            for metric in (
                "affected_share_gt1min_pct",
                "mean_minutes_change",
            ):
                _assert_close(
                    f"baseline equity {destination}.{group}.{metric}",
                    actual_destination["groups"][group][metric],
                    expected_destination["groups"][group][metric],
                )
                checked_equity += 1
    return {
        "status": "PASS",
        "route_id": str(actual_route["id"]),
        "route_peak_time": actual_route["peak_departure_time"],
        "trip_id": str(actual_trip["id"]),
        "trip_peak_time": actual_trip["peak_departure_time"],
        "equity_metrics_checked": checked_equity,
    }


def _equity_stability(cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for destination in DESTINATION_SPECS:
        destination_result: dict[str, Any] = {}
        for group in ("65plus", "75plus", "85plus"):
            metrics: dict[str, Any] = {}
            for metric in (
                "affected_share_gt1min_gap_pp",
                "mean_minutes_change_gap",
            ):
                values = {
                    case_id: case_result["equity"][destination]["gaps_vs_all"][group][metric]
                    for case_id, case_result in cases.items()
                }
                metrics[metric] = direction_stability(values)
            destination_result[group] = metrics
        result[destination] = destination_result
    return result


def _boundary_conditions(
    route_stability: dict[str, Any],
    trip_stability: dict[str, Any],
    equity_stability: dict[str, Any],
) -> dict[str, Any]:
    equity_changes: dict[str, list[str]] = {}
    for destination, groups in equity_stability.items():
        for group, metrics in groups.items():
            for metric, stability in metrics.items():
                for case_id in stability["changed_direction_cases"]:
                    equity_changes.setdefault(case_id, []).append(
                        f"{destination}.{group}.{metric}"
                    )
    all_cases = set(route_stability["changed_top1_cases"])
    all_cases.update(trip_stability["changed_top1_cases"])
    all_cases.update(equity_changes)
    return {
        "case_ids": sorted(all_cases),
        "route_top1_changed": route_stability["changed_top1_cases"],
        "trip_top1_changed": trip_stability["changed_top1_cases"],
        "trip_outside_top3": trip_stability["outside_top_k_cases"],
        "equity_direction_changes": equity_changes,
    }


def build(output: Path) -> dict[str, Any]:
    validate_cases()
    output.mkdir(parents=True, exist_ok=True)
    predecessor = output / "a1_12"
    predecessor_summary = build_a1_12(predecessor)
    if predecessor_summary.get("stage") != "A1.12":
        raise ValueError("A1.13 predecessor did not finish at A1.12")

    feed = load_feed(fetch(GTFS_URL))
    bbox = gtfs_bbox(feed)
    population_rows = first_csv_rows(fetch(POP_URL))
    osm = fetch_osm(bbox)
    graph, node_coordinates = walking_graph_from_overpass(osm)
    errors = graph.validate()
    if errors:
        raise ValueError("A1.13 walking graph invalid: " + "; ".join(errors[:20]))
    index = CoordinateIndex(node_coordinates)

    stops = [
        {
            "id": row["stop_id"],
            "stop_id": row["stop_id"],
            "name": row["stop_name"],
            "lat": float(row["stop_lat"]),
            "lon": float(row["stop_lon"]),
        }
        for row in feed.files["stops.txt"]
    ]
    stop_nodes, _ = snap_points(stops, index, max_snap_km=0.5)
    if len(stop_nodes) != len(stops):
        raise ValueError("A1.13 requires all GTFS stops to snap")
    zones = zones_to_nodes(population_zones(population_rows, bbox), index)
    if not zones:
        raise ValueError("A1.13 has no population zones")
    age_by_zone = _age_weights(predecessor)
    if set(age_by_zone) != {str(zone["zone_id"]) for zone in zones}:
        raise ValueError("A1.13 age-weight zone contract changed")

    facility_records: dict[str, list[dict[str, Any]]] = {
        "hospital": _point_records(predecessor / "facilities.geojson"),
        "emergency": _point_records(predecessor / "shelters.geojson", kind="emergency"),
        "general": _point_records(predecessor / "shelters.geojson", kind="general"),
        "welfare": _point_records(predecessor / "shelters.geojson", kind="welfare"),
    }
    base_facility_walk: dict[str, dict[str, float]] = {}
    for destination, records in facility_records.items():
        nodes, _ = snap_points(records, index, max_snap_km=0.5)
        if not nodes:
            raise ValueError(f"A1.13 has no snapped {destination} destination")
        base_facility_walk[destination] = min_walk_minutes_to_facility(
            graph, nodes.values()
        )

    base_stop_walk = stop_walk_times(graph, stop_nodes)
    connections = sorted(
        feed.connections(ANALYSIS_DATE),
        key=lambda item: (item["departure_seconds"], item["arrival_seconds"]),
    )
    if not connections:
        raise ValueError(f"A1.13 GTFS has no connections on {ANALYSIS_DATE}")
    trip_rows = {str(row["trip_id"]): row for row in feed.files["trips.txt"]}
    trip_routes = {
        trip_id: str(row["route_id"])
        for trip_id, row in trip_rows.items()
    }
    route_rows = {str(row["route_id"]): row for row in feed.files["routes.txt"]}
    route_names = {
        route_id: row.get("route_long_name") or row.get("route_short_name") or route_id
        for route_id, row in route_rows.items()
    }
    all_trip_ids = sorted({str(connection["trip_id"]) for connection in connections})
    all_route_ids = sorted({trip_routes[trip_id] for trip_id in all_trip_ids})
    first_departure: dict[str, int] = {}
    for connection in connections:
        first_departure.setdefault(
            str(connection["trip_id"]), int(connection["departure_seconds"])
        )
    right_loop_routes = set(
        str(item)
        for item in predecessor_summary.get("scenario", {}).get("disabled_route_ids", [])
    )
    if not right_loop_routes:
        right_loop_routes = {
            route_id
            for route_id in all_route_ids
            if "右回り" in route_names.get(route_id, "")
        }
    if not right_loop_routes:
        raise ValueError("A1.13 clockwise reference outage route not found")

    case_results: dict[str, dict[str, Any]] = {}
    for case in SENSITIVITY_CASES:
        case_results[case.id] = _build_case(
            case=case,
            zones=zones,
            connections=connections,
            trip_routes=trip_routes,
            trip_rows=trip_rows,
            route_names=route_names,
            all_route_ids=all_route_ids,
            all_trip_ids=all_trip_ids,
            first_departure=first_departure,
            stop_nodes=stop_nodes,
            base_stop_walk=base_stop_walk,
            base_facility_walk=base_facility_walk,
            right_loop_routes=right_loop_routes,
            age_by_zone=age_by_zone,
        )

    baseline_equivalence = _verify_baseline_equivalence(
        case_results["baseline"], predecessor
    )
    route_rankings = {
        case_id: result["route_day_ranking"]
        for case_id, result in case_results.items()
    }
    trip_rankings = {
        case_id: result["trip_day_ranking"]
        for case_id, result in case_results.items()
    }
    route_stability = reference_stability(route_rankings, top_k=3)
    trip_stability = reference_stability(trip_rankings, top_k=3)
    equity_stability = _equity_stability(case_results)
    boundaries = _boundary_conditions(
        route_stability, trip_stability, equity_stability
    )

    provenance = make_provenance(
        "a1-13-ozu-robustness-uncertainty",
        "C",
        "minimal-multimodal-v0.1.13",
        [
            {
                "dataset_id": "ozu_gururin_gtfs_20260401",
                "source": GTFS_LANDING,
                "classification": "A",
                "license": "CC BY 4.0",
            },
            {
                "dataset_id": "ozu_population_100m_2020_age",
                "source": POP_LANDING,
                "classification": "B",
                "license": "CC BY",
            },
            {
                "dataset_id": "a1_12_verified_predecessor",
                "source": "outputs/a1_13/a1_12",
                "classification": "C",
                "usage": "protected predecessor result; Golden regression remains mandatory",
            },
        ],
        {
            "analysis_date": ANALYSIS_DATE.isoformat(),
            "criticality_destination": "hospital",
            "equity_destinations": list(DESTINATION_SPECS),
            "population_groups": list(AGE_GROUP_FIELDS),
            "temporal_start": f"{TEMPORAL_START_HOUR:02d}:00",
            "temporal_end": f"{TEMPORAL_END_HOUR:02d}:00",
            "temporal_step_minutes": TEMPORAL_STEP_MINUTES,
            "sensitivity_cases": [case.as_dict() for case in SENSITIVITY_CASES],
            "walking_time_transform": "baseline_minutes * 4.8 / sensitivity_speed_kmh",
            "equity_zone_minute_precision": 2,
            "ranking_order": [
                "population_with_gt_1min_increase desc",
                "mean_minutes_change desc",
                "id asc",
            ],
            "direction_epsilon": 0.0005,
            "composite_robustness_score": False,
        },
        scenario_id="ozu-a1-13-sensitivity-analysis",
        limitations=[
            "A1.13 is deterministic sensitivity analysis, not a probabilistic uncertainty model, confidence interval or failure probability.",
            "Sensitivity cases perturb one model assumption at a time and do not represent joint worst-case mobility conditions.",
            "Criticality ranking remains hospital-access consequence only; ridership, operating cost and failure likelihood are not included.",
            "Equity direction is descriptive and is not a test of statistical significance or a normative priority score.",
            "A1.13 equity aggregation preserves the same two-decimal zone travel-time precision consumed by the A1.12 public GeoJSON contract.",
            "Age-group results remain based on the 2020 simplified 100 m population source; current 2026 regional totals are not spatially downscaled.",
            "All outages remain D stress-test assumptions rather than damage forecasts.",
        ],
        repository=ROOT,
    )

    robustness_summary = {
        "stage": "A1.13",
        "status": "computed",
        "analysis_date": ANALYSIS_DATE.isoformat(),
        "criticality_destination": "hospital",
        "case_count": len(SENSITIVITY_CASES),
        "slots_per_case": 16,
        "case_slot_combinations": len(SENSITIVITY_CASES) * 16,
        "case_ids": [case.id for case in SENSITIVITY_CASES],
        "composite_score": False,
        "baseline_equivalence": baseline_equivalence,
        "route_stability": route_stability,
        "trip_stability": trip_stability,
        "equity_direction_stability": equity_stability,
        "boundary_conditions": boundaries,
        "interpretation": {
            "ranking_stability": "counts show how many pre-registered sensitivity cases preserve the baseline candidate rank; they are not probabilities",
            "equity_direction": "same-direction counts show whether descriptive gaps retain their sign; they are not significance tests",
            "case_selection": "all seven pre-registered cases are evaluated; no post-hoc case filtering",
        },
    }
    cases_payload = {
        "stage": "A1.13",
        "case_registry": [case.as_dict() for case in SENSITIVITY_CASES],
        "criticality_time_window": {
            "start": f"{TEMPORAL_START_HOUR:02d}:00",
            "end": f"{TEMPORAL_END_HOUR:02d}:00",
            "step_minutes": TEMPORAL_STEP_MINUTES,
            "slots": 16,
        },
        "cases": case_results,
    }

    summary = dict(predecessor_summary)
    summary.update(
        {
            "stage": "A1.13",
            "title": "大洲市 Robustness / Uncertainty Analysis",
            "provenance": provenance,
            "robustness_analysis": {
                "case_count": robustness_summary["case_count"],
                "case_slot_combinations": robustness_summary[
                    "case_slot_combinations"
                ],
                "reference_route_id": route_stability["reference_id"],
                "reference_route_top1_cases": route_stability["top1_count"],
                "reference_route_top3_cases": route_stability["top3_count"],
                "reference_trip_id": trip_stability["reference_id"],
                "reference_trip_top1_cases": trip_stability["top1_count"],
                "reference_trip_top3_cases": trip_stability["top3_count"],
                "boundary_case_ids": boundaries["case_ids"],
                "composite_score": False,
                "baseline_equivalence": baseline_equivalence["status"],
            },
        }
    )
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "robustness_summary.json").write_text(
        json.dumps(robustness_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output / "robustness_cases.json").write_text(
        json.dumps(cases_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "stage": "A1.13",
                "case_count": robustness_summary["case_count"],
                "case_slot_combinations": robustness_summary[
                    "case_slot_combinations"
                ],
                "baseline_equivalence": baseline_equivalence,
                "route_stability": route_stability,
                "trip_stability": trip_stability,
                "boundary_case_ids": boundaries["case_ids"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=ROOT / "outputs" / "a1_13"
    )
    args = parser.parse_args()
    summary = build(args.output)
    robustness = summary.get("robustness_analysis", {})
    return 0 if summary.get("stage") == "A1.13" and robustness.get("case_count") == 7 else 2


if __name__ == "__main__":
    raise SystemExit(main())
