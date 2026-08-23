"""A1.11: time-dependent route/trip criticality for the Ozu hospital-access model.

A1.9 is regenerated first so all predecessor hospital/shelter outputs remain
available. A1.11 then evaluates leave-one-out route/trip outages at each hourly
slot from 06:00 through 21:00. Ranking is unchanged from A1.8:
>1 minute affected population descending, population-weighted mean degradation
descending, then stable identifier.

A route/trip with no remaining boardable GTFS connection at a slot is retained
in the ranking with zero impact and evaluated=false rather than wasting a full
routing run. This is a deterministic sensitivity analysis, not a failure
probability or ridership importance score.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from accessibility.multimodal import (
    CoordinateIndex,
    extract_facilities,
    min_walk_minutes_to_facility,
    stop_transfer_edges,
    stop_walk_times,
    walking_graph_from_overpass,
)
from accessibility.official_facilities import official_hospitals, verify_osm_hospitals
from common.provenance import make_provenance
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
from scripts.build_network.build_a1_5 import (
    OFFICIAL_MEDICAL_AS_OF,
    OFFICIAL_MEDICAL_LANDING,
    OFFICIAL_MEDICAL_URL,
)
from scripts.build_network.build_a1_6 import MAX_TRANSFER_WALK_MINUTES, TRANSFER_BUFFER_MINUTES
from scripts.build_network.build_a1_7 import (
    TEMPORAL_END_HOUR,
    TEMPORAL_START_HOUR,
    TEMPORAL_STEP_MINUTES,
    impact_metrics,
    time_label,
)
from scripts.build_network.build_a1_8 import (
    assert_outage_monotonic,
    evaluate_at,
    ranking_key,
)
from scripts.build_network.build_a1_9 import (
    SHELTER_AS_OF,
    SHELTER_LANDING,
    build as build_a1_9,
)


def zero_impact() -> dict[str, float]:
    return {
        "population_with_gt_1min_increase": 0.0,
        "population_with_gt_5min_increase": 0.0,
        "population_with_gt_10min_increase": 0.0,
        "accessibility_loss_30min_population": 0.0,
        "accessibility_loss_60min_population": 0.0,
        "mean_minutes_change": 0.0,
    }


def material_impact(impact: dict[str, Any]) -> bool:
    return any(
        float(impact.get(key, 0) or 0) > 1e-6
        for key in (
            "population_with_gt_1min_increase",
            "accessibility_loss_30min_population",
            "accessibility_loss_60min_population",
            "mean_minutes_change",
        )
    )


def first_material(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((item for item in items if material_impact(item["impact"])), None)


def remaining_candidates(
    connections: list[dict[str, Any]],
    departure_seconds: int,
) -> tuple[set[str], int]:
    future = [c for c in connections if int(c["departure_seconds"]) >= departure_seconds]
    return {str(c["trip_id"]) for c in future}, len(future)


def peak_event(rows: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for row in rows:
        for item in row[key]:
            if material_impact(item["impact"]):
                candidates.append({"departure_time": row["departure_time"], **item})
    if not candidates:
        return None
    return min(candidates, key=lambda item: (
        -float(item["impact"]["population_with_gt_1min_increase"]),
        -float(item["impact"]["mean_minutes_change"]),
        str(item["id"]),
        str(item["departure_time"]),
    ))


def build(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)

    # Preserve all predecessor outputs, including shelter accessibility and the
    # A1.10 destination-switcher dependencies.
    predecessor = build_a1_9(output)

    feed = load_feed(fetch(GTFS_URL))
    bbox = gtfs_bbox(feed)
    population_rows = first_csv_rows(fetch(POP_URL))
    osm = fetch_osm(bbox)
    official_payload = fetch(OFFICIAL_MEDICAL_URL)

    graph, node_coordinates = walking_graph_from_overpass(osm)
    graph_errors = graph.validate()
    if graph_errors:
        raise ValueError("A1.11 walking graph invalid: " + "; ".join(graph_errors[:20]))
    index = CoordinateIndex(node_coordinates)

    official = official_hospitals(official_payload, bbox)
    osm_hospitals = extract_facilities(osm, allowed={"hospital"})
    verified_hospitals, verification = verify_osm_hospitals(osm_hospitals, official)
    if not official or not verified_hospitals:
        raise ValueError("A1.11 official hospital verification gate failed")
    facility_nodes, _ = snap_points(
        [dict(item, id=item["id"]) for item in verified_hospitals], index, max_snap_km=0.5
    )
    if not facility_nodes:
        raise ValueError("A1.11 has no verified hospital snapped to walking network")

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
    if len(stop_nodes) != len(feed.files["stops.txt"]):
        raise ValueError("A1.11 requires all GTFS stops to snap")
    zones = zones_to_nodes(population_zones(population_rows, bbox), index)
    if not zones:
        raise ValueError("A1.11 has no population zones")

    facility_walk = min_walk_minutes_to_facility(graph, facility_nodes.values())
    stop_walk = stop_walk_times(graph, stop_nodes)
    transfers = stop_transfer_edges(
        stop_walk,
        stop_nodes,
        max_walk_minutes=MAX_TRANSFER_WALK_MINUTES,
        transfer_buffer_minutes=TRANSFER_BUFFER_MINUTES,
    )
    if not transfers:
        raise ValueError("A1.11 walking transfer graph is empty")

    connections = sorted(
        feed.connections(ANALYSIS_DATE),
        key=lambda item: (item["departure_seconds"], item["arrival_seconds"]),
    )
    if not connections:
        raise ValueError(f"A1.11 GTFS has no connections on {ANALYSIS_DATE}")

    trip_rows = {str(row["trip_id"]): row for row in feed.files["trips.txt"]}
    trip_routes = {trip_id: str(row["route_id"]) for trip_id, row in trip_rows.items()}
    route_rows = {str(row["route_id"]): row for row in feed.files["routes.txt"]}
    route_names = {
        route_id: row.get("route_long_name") or row.get("route_short_name") or route_id
        for route_id, row in route_rows.items()
    }
    all_trip_ids = sorted({str(c["trip_id"]) for c in connections})
    all_route_ids = sorted({trip_routes[trip_id] for trip_id in all_trip_ids})
    # connections are sorted by departure, so setdefault captures each trip's
    # first departure in a single O(connections) pass instead of rescanning the
    # full list once per trip.
    first_departure: dict[str, int] = {}
    for connection in connections:
        first_departure.setdefault(str(connection["trip_id"]), int(connection["departure_seconds"]))

    rows: list[dict[str, Any]] = []
    total_route_evaluations = 0
    total_trip_evaluations = 0
    step_seconds = TEMPORAL_STEP_MINUTES * 60

    for departure_seconds in range(
        TEMPORAL_START_HOUR * 3600,
        TEMPORAL_END_HOUR * 3600 + 1,
        step_seconds,
    ):
        label = time_label(departure_seconds)
        baseline_minutes, baseline = evaluate_at(
            departure_seconds=departure_seconds,
            zones=zones,
            connections=connections,
            trip_routes=trip_routes,
            stop_walk=stop_walk,
            facility_walk_by_node=facility_walk,
            stop_nodes=stop_nodes,
            transfers=transfers,
        )
        future_trip_ids, remaining_connections = remaining_candidates(connections, departure_seconds)
        future_route_ids = {trip_routes[trip_id] for trip_id in future_trip_ids}

        route_ranking: list[dict[str, Any]] = []
        for route_id in all_route_ids:
            if route_id not in future_route_ids:
                route_ranking.append({
                    "id": route_id,
                    "route_name": route_names.get(route_id, route_id),
                    "remaining_trip_count": 0,
                    "evaluated": False,
                    "skip_reason": "no_remaining_boardable_connection",
                    "impact": zero_impact(),
                })
                continue
            outage_minutes, outage = evaluate_at(
                departure_seconds=departure_seconds,
                zones=zones,
                connections=connections,
                trip_routes=trip_routes,
                stop_walk=stop_walk,
                facility_walk_by_node=facility_walk,
                stop_nodes=stop_nodes,
                transfers=transfers,
                disabled_routes={route_id},
            )
            assert_outage_monotonic(baseline_minutes, outage_minutes, f"{label}:route:{route_id}")
            total_route_evaluations += 1
            route_ranking.append({
                "id": route_id,
                "route_name": route_names.get(route_id, route_id),
                "remaining_trip_count": sum(1 for tid in future_trip_ids if trip_routes[tid] == route_id),
                "evaluated": True,
                "impact": impact_metrics(zones, baseline_minutes, outage_minutes, baseline, outage),
            })
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
                trip_ranking.append({
                    **common,
                    "evaluated": False,
                    "skip_reason": "no_remaining_boardable_connection",
                    "impact": zero_impact(),
                })
                continue
            outage_minutes, outage = evaluate_at(
                departure_seconds=departure_seconds,
                zones=zones,
                connections=connections,
                trip_routes=trip_routes,
                stop_walk=stop_walk,
                facility_walk_by_node=facility_walk,
                stop_nodes=stop_nodes,
                transfers=transfers,
                disabled_trips={trip_id},
            )
            assert_outage_monotonic(baseline_minutes, outage_minutes, f"{label}:trip:{trip_id}")
            total_trip_evaluations += 1
            trip_ranking.append({
                **common,
                "evaluated": True,
                "impact": impact_metrics(zones, baseline_minutes, outage_minutes, baseline, outage),
            })
        trip_ranking.sort(key=ranking_key)
        for rank, item in enumerate(trip_ranking, 1):
            item["rank"] = rank

        rows.append({
            "departure_time": label,
            "departure_seconds": departure_seconds,
            "remaining_boardable_connections": remaining_connections,
            "remaining_trip_count": len(future_trip_ids),
            "remaining_route_count": len(future_route_ids),
            "top_route": first_material(route_ranking),
            "top_trip": first_material(trip_ranking),
            "route_ranking": route_ranking,
            "trip_ranking": trip_ranking,
        })

    peak_route = peak_event(rows, "route_ranking")
    peak_trip = peak_event(rows, "trip_ranking")
    top_route_ids = [row["top_route"]["id"] for row in rows if row["top_route"]]
    top_trip_ids = [row["top_trip"]["id"] for row in rows if row["top_trip"]]
    route_changes = sum(1 for a, b in zip(top_route_ids, top_route_ids[1:], strict=False) if a != b)
    trip_changes = sum(1 for a, b in zip(top_trip_ids, top_trip_ids[1:], strict=False) if a != b)

    provenance = make_provenance(
        "a1-11-ozu-time-dependent-criticality",
        "C",
        "minimal-multimodal-v0.1.11",
        [
            {"dataset_id": "ozu_gururin_gtfs_20260401", "source": GTFS_LANDING, "classification": "A", "license": "CC BY 4.0"},
            {"dataset_id": "ozu_shelters_20260401", "source": SHELTER_LANDING, "classification": "A", "license": "CC BY 4.0", "usage": "preserved predecessor A1.9 destination analysis"},
            {"dataset_id": "ozu_population_100m_2020", "source": POP_LANDING, "classification": "B", "license": "CC BY"},
            {"dataset_id": "osm_ozu_gtfs_envelope", "source": "https://www.openstreetmap.org/copyright", "classification": "B", "license": "ODbL 1.0"},
            {"dataset_id": "ehime_medical_basic_information_20260801", "source": OFFICIAL_MEDICAL_LANDING, "classification": "A", "license": "official website publication; redistribution not asserted", "usage": "transient hospital verification only; raw rows are not published"},
        ],
        {
            "analysis_date": ANALYSIS_DATE.isoformat(),
            "analysis_destination": "hospital",
            "criticality_method": "hourly leave-one-out active route/trip",
            "ranking_order": ["population_with_gt_1min_increase desc", "mean_minutes_change desc", "id asc"],
            "temporal_start": f"{TEMPORAL_START_HOUR:02d}:00",
            "temporal_end": f"{TEMPORAL_END_HOUR:02d}:00",
            "temporal_step_minutes": TEMPORAL_STEP_MINUTES,
            "inactive_candidate_rule": "no remaining GTFS connection at/after slot => zero impact, evaluated=false",
            "walking_speed_kmh": 4.8,
            "max_access_walk_minutes": 20,
            "max_transfer_walk_minutes": MAX_TRANSFER_WALK_MINUTES,
            "transfer_buffer_minutes": TRANSFER_BUFFER_MINUTES,
            "official_registry_as_of": OFFICIAL_MEDICAL_AS_OF,
            "shelter_source_as_of": SHELTER_AS_OF,
        },
        scenario_id="ozu-time-dependent-service-criticality",
        limitations=[
            "A1.11 is a modelled hospital-access sensitivity analysis, not a route failure probability, ridership measure or operational priority score.",
            "Each outage is applied independently at the selected departure time; cascading failures and vehicle circulation are not modelled.",
            "Routes/trips with no remaining boardable connection at a slot are reported with zero impact and evaluated=false.",
            "Ranking uses accessibility consequence only; ridership, cost, equity weights and vehicle availability are not included.",
            "Hourly sampling from 06:00 to 21:00 can miss shorter peaks between sample times.",
            "Hospital destinations are OSM features verified against the 2026-08-01 Ehime official medical registry.",
            "A1.9 shelter accessibility is preserved unchanged and is not included in the A1.11 criticality ranking.",
            "All route/trip outages are D stress-test assumptions, not damage forecasts.",
        ],
        repository=ROOT,
    )

    summary = dict(predecessor)
    summary.update({
        "stage": "A1.11",
        "title": "大洲市 Time-dependent Route / Trip Criticality",
        "provenance": provenance,
        "time_dependent_criticality": {
            "analysis_destination": "hospital",
            "start": f"{TEMPORAL_START_HOUR:02d}:00",
            "end": f"{TEMPORAL_END_HOUR:02d}:00",
            "step_minutes": TEMPORAL_STEP_MINUTES,
            "slots": len(rows),
            "ranking_rule": "population_with_gt_1min_increase desc, mean_minutes_change desc, id asc",
            "total_route_evaluations": total_route_evaluations,
            "total_trip_evaluations": total_trip_evaluations,
            "slots_with_material_route_impact": sum(1 for row in rows if row["top_route"]),
            "slots_with_material_trip_impact": sum(1 for row in rows if row["top_trip"]),
            "top_route_changes": route_changes,
            "top_trip_changes": trip_changes,
            "peak_route_event": peak_route,
            "peak_trip_event": peak_trip,
        },
    })
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    payload = {
        "stage": "A1.11",
        "source_stages": ["A1.7", "A1.8", "A1.9"],
        "analysis_destination": "hospital",
        "analysis_date": ANALYSIS_DATE.isoformat(),
        "time_window": summary["time_dependent_criticality"],
        "route_ids": all_route_ids,
        "trip_ids": all_trip_ids,
        "rows": rows,
    }
    (output / "time_dependent_criticality.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps({
        "stage": "A1.11",
        "slots": len(rows),
        "route_evaluations": total_route_evaluations,
        "trip_evaluations": total_trip_evaluations,
        "slots_with_material_route_impact": summary["time_dependent_criticality"]["slots_with_material_route_impact"],
        "slots_with_material_trip_impact": summary["time_dependent_criticality"]["slots_with_material_trip_impact"],
        "peak_route_event": peak_route,
        "peak_trip_event": peak_trip,
        "hospital_verification": verification,
    }, ensure_ascii=False, indent=2))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "a1_11")
    args = parser.parse_args()
    summary = build(args.output)
    td = summary["time_dependent_criticality"]
    return 0 if td["slots"] == 16 and td["total_route_evaluations"] > 0 and td["total_trip_evaluations"] > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())