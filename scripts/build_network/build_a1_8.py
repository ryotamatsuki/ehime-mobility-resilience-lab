"""A1.8: route/trip leave-one-out criticality for the Ozu A1 model.

The A1.7 full-day profile is retained. Criticality itself is evaluated at the
stable 08:00 reference time: each active route and each active trip is removed
one at a time, then the same population-to-hospital accessibility calculation is
rerun. Ranking is transparent: >1 minute affected population descending, then
population-weighted mean degradation descending, then stable identifier.
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

from accessibility.multimodal import (
    CoordinateIndex,
    earliest_arrival_minutes,
    extract_facilities,
    min_walk_minutes_to_facility,
    stop_transfer_edges,
    stop_walk_times,
    summarize_population_access,
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
    geojson_points,
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
    REFERENCE_DEPARTURE_SECONDS,
    TEMPORAL_END_HOUR,
    TEMPORAL_START_HOUR,
    TEMPORAL_STEP_MINUTES,
    impact_metrics,
    time_label,
)


def evaluate_at(
    *,
    departure_seconds: int,
    zones: list[dict[str, Any]],
    connections: list[dict[str, Any]],
    trip_routes: dict[str, str],
    stop_walk: dict[str, dict[str, float]],
    facility_walk_by_node: dict[str, float],
    stop_nodes: dict[str, str],
    transfers: dict[str, list[dict[str, float | str]]],
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
            stop_transfers=transfers,
        )
    return values, summarize_population_access(zones, values)


def assert_outage_monotonic(
    baseline_minutes: dict[str, float], outage_minutes: dict[str, float], label: str
) -> None:
    for zone_id, before in baseline_minutes.items():
        after = outage_minutes.get(zone_id, math.inf)
        if math.isfinite(before) and math.isfinite(after) and after + 1e-6 < before:
            raise ValueError(f"{label} unexpectedly improves zone {zone_id}")
        if not math.isfinite(before) and math.isfinite(after):
            raise ValueError(f"{label} unexpectedly makes unreachable zone {zone_id} reachable")


def ranking_key(item: dict[str, Any]) -> tuple[float, float, str]:
    impact = item["impact"]
    return (
        -float(impact["population_with_gt_1min_increase"]),
        -float(impact["mean_minutes_change"]),
        str(item["id"]),
    )


def build(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)

    feed = load_feed(fetch(GTFS_URL))
    bbox = gtfs_bbox(feed)
    population_rows = first_csv_rows(fetch(POP_URL))
    osm = fetch_osm(bbox)
    official_payload = fetch(OFFICIAL_MEDICAL_URL)

    graph, node_coordinates = walking_graph_from_overpass(osm)
    graph_errors = graph.validate()
    if graph_errors:
        raise ValueError("walking graph invalid: " + "; ".join(graph_errors[:20]))
    index = CoordinateIndex(node_coordinates)

    official = official_hospitals(official_payload, bbox)
    osm_hospitals = extract_facilities(osm, allowed={"hospital"})
    verified_hospitals, verification = verify_osm_hospitals(osm_hospitals, official)
    if not official or not verified_hospitals:
        raise ValueError("official hospital verification gate failed")
    facility_nodes, facilities = snap_points(
        [dict(item, id=item["id"]) for item in verified_hospitals], index, max_snap_km=0.5
    )
    if not facility_nodes:
        raise ValueError("no verified hospital snapped to walking network")

    stops = [
        {
            "id": row["stop_id"], "stop_id": row["stop_id"], "name": row["stop_name"],
            "lat": float(row["stop_lat"]), "lon": float(row["stop_lon"]),
        }
        for row in feed.files["stops.txt"]
    ]
    stop_nodes, stops = snap_points(stops, index, max_snap_km=0.5)
    if len(stop_nodes) != len(feed.files["stops.txt"]):
        raise ValueError("A1.8 requires all GTFS stops to snap")
    zones = zones_to_nodes(population_zones(population_rows, bbox), index)
    if not zones:
        raise ValueError("no population zones available")

    facility_walk = min_walk_minutes_to_facility(graph, facility_nodes.values())
    stop_walk = stop_walk_times(graph, stop_nodes)
    transfers = stop_transfer_edges(
        stop_walk, stop_nodes,
        max_walk_minutes=MAX_TRANSFER_WALK_MINUTES,
        transfer_buffer_minutes=TRANSFER_BUFFER_MINUTES,
    )
    if not transfers:
        raise ValueError("walking transfer graph is empty")

    connections = sorted(
        feed.connections(ANALYSIS_DATE),
        key=lambda item: (item["departure_seconds"], item["arrival_seconds"]),
    )
    if not connections:
        raise ValueError(f"GTFS has no connections on {ANALYSIS_DATE}")

    trip_rows = {str(row["trip_id"]): row for row in feed.files["trips.txt"]}
    trip_routes = {trip_id: str(row["route_id"]) for trip_id, row in trip_rows.items()}
    route_rows = {str(row["route_id"]): row for row in feed.files["routes.txt"]}
    route_names = {
        route_id: row.get("route_long_name") or row.get("route_short_name") or route_id
        for route_id, row in route_rows.items()
    }
    active_trip_ids = sorted({str(c["trip_id"]) for c in connections})
    active_route_ids = sorted({trip_routes[trip_id] for trip_id in active_trip_ids})
    if not active_route_ids or not active_trip_ids:
        raise ValueError("no active routes/trips for criticality")

    right_loop_routes = {rid for rid in active_route_ids if "右回り" in route_names.get(rid, "")}
    if not right_loop_routes:
        raise ValueError("clockwise reference outage route not found")

    # Reference 08:00 baseline and existing Scenario A.
    baseline_minutes, baseline = evaluate_at(
        departure_seconds=REFERENCE_DEPARTURE_SECONDS,
        zones=zones, connections=connections, trip_routes=trip_routes, stop_walk=stop_walk,
        facility_walk_by_node=facility_walk, stop_nodes=stop_nodes, transfers=transfers,
    )
    disrupted_minutes, disrupted = evaluate_at(
        departure_seconds=REFERENCE_DEPARTURE_SECONDS,
        zones=zones, connections=connections, trip_routes=trip_routes, stop_walk=stop_walk,
        facility_walk_by_node=facility_walk, stop_nodes=stop_nodes, transfers=transfers,
        disabled_routes=right_loop_routes,
    )
    reference_impact = impact_metrics(zones, baseline_minutes, disrupted_minutes, baseline, disrupted)

    # Preserve A1.7 temporal profile in the successor output.
    temporal_rows: list[dict[str, Any]] = []
    step = TEMPORAL_STEP_MINUTES * 60
    for departure_seconds in range(TEMPORAL_START_HOUR * 3600, TEMPORAL_END_HOUR * 3600 + 1, step):
        b_minutes, b = evaluate_at(
            departure_seconds=departure_seconds,
            zones=zones, connections=connections, trip_routes=trip_routes, stop_walk=stop_walk,
            facility_walk_by_node=facility_walk, stop_nodes=stop_nodes, transfers=transfers,
        )
        d_minutes, d = evaluate_at(
            departure_seconds=departure_seconds,
            zones=zones, connections=connections, trip_routes=trip_routes, stop_walk=stop_walk,
            facility_walk_by_node=facility_walk, stop_nodes=stop_nodes, transfers=transfers,
            disabled_routes=right_loop_routes,
        )
        temporal_rows.append({
            "departure_time": time_label(departure_seconds),
            "departure_seconds": departure_seconds,
            "baseline": b,
            "disrupted": d,
            "impact": impact_metrics(zones, b_minutes, d_minutes, b, d),
        })

    route_ranking: list[dict[str, Any]] = []
    for route_id in active_route_ids:
        outage_minutes, outage = evaluate_at(
            departure_seconds=REFERENCE_DEPARTURE_SECONDS,
            zones=zones, connections=connections, trip_routes=trip_routes, stop_walk=stop_walk,
            facility_walk_by_node=facility_walk, stop_nodes=stop_nodes, transfers=transfers,
            disabled_routes={route_id},
        )
        assert_outage_monotonic(baseline_minutes, outage_minutes, f"route:{route_id}")
        route_ranking.append({
            "id": route_id,
            "route_name": route_names.get(route_id, route_id),
            "active_trip_count": sum(1 for tid in active_trip_ids if trip_routes[tid] == route_id),
            "impact": impact_metrics(zones, baseline_minutes, outage_minutes, baseline, outage),
        })
    route_ranking.sort(key=ranking_key)
    for index_rank, item in enumerate(route_ranking, 1):
        item["rank"] = index_rank

    first_departure = {
        trip_id: min(int(c["departure_seconds"]) for c in connections if str(c["trip_id"]) == trip_id)
        for trip_id in active_trip_ids
    }
    trip_ranking: list[dict[str, Any]] = []
    for trip_id in active_trip_ids:
        outage_minutes, outage = evaluate_at(
            departure_seconds=REFERENCE_DEPARTURE_SECONDS,
            zones=zones, connections=connections, trip_routes=trip_routes, stop_walk=stop_walk,
            facility_walk_by_node=facility_walk, stop_nodes=stop_nodes, transfers=transfers,
            disabled_trips={trip_id},
        )
        assert_outage_monotonic(baseline_minutes, outage_minutes, f"trip:{trip_id}")
        trip_row = trip_rows[trip_id]
        trip_ranking.append({
            "id": trip_id,
            "route_id": trip_routes[trip_id],
            "route_name": route_names.get(trip_routes[trip_id], trip_routes[trip_id]),
            "trip_headsign": trip_row.get("trip_headsign") or "",
            "first_departure": time_label(first_departure[trip_id]),
            "impact": impact_metrics(zones, baseline_minutes, outage_minutes, baseline, outage),
        })
    trip_ranking.sort(key=ranking_key)
    for index_rank, item in enumerate(trip_ranking, 1):
        item["rank"] = index_rank

    worst_affected = max(temporal_rows, key=lambda r: float(r["impact"]["population_with_gt_1min_increase"]))
    worst_mean = max(temporal_rows, key=lambda r: float(r["impact"]["mean_minutes_change"]))
    lowest = min(temporal_rows, key=lambda r: float(r["impact"]["population_with_gt_1min_increase"]))

    provenance = make_provenance(
        "a1-8-ozu-route-trip-criticality",
        "C",
        "minimal-multimodal-v0.1.8",
        [
            {"dataset_id": "ozu_gururin_gtfs_20260401", "source": GTFS_LANDING, "classification": "A", "license": "CC BY 4.0"},
            {"dataset_id": "ozu_population_100m_2020", "source": POP_LANDING, "classification": "B", "license": "CC BY"},
            {"dataset_id": "osm_ozu_gtfs_envelope", "source": "https://www.openstreetmap.org/copyright", "classification": "B", "license": "ODbL 1.0"},
            {"dataset_id": "ehime_medical_basic_information_20260801", "source": OFFICIAL_MEDICAL_LANDING, "classification": "A", "license": "official website publication; redistribution not asserted", "usage": "transient verification only; raw rows are not published"},
        ],
        {
            "analysis_date": ANALYSIS_DATE.isoformat(),
            "criticality_reference_time": "08:00:00",
            "criticality_method": "leave-one-out active route/trip",
            "ranking_order": ["population_with_gt_1min_increase desc", "mean_minutes_change desc", "id asc"],
            "temporal_start": f"{TEMPORAL_START_HOUR:02d}:00",
            "temporal_end": f"{TEMPORAL_END_HOUR:02d}:00",
            "temporal_step_minutes": TEMPORAL_STEP_MINUTES,
            "walking_speed_kmh": 4.8,
            "max_access_walk_minutes": 20,
            "max_transfer_walk_minutes": MAX_TRANSFER_WALK_MINUTES,
            "transfer_buffer_minutes": TRANSFER_BUFFER_MINUTES,
            "official_registry_as_of": OFFICIAL_MEDICAL_AS_OF,
        },
        scenario_id="ozu-service-criticality",
        limitations=[
            "A1.8 criticality is an 08:00 leave-one-out sensitivity analysis, not a failure probability or operational importance score.",
            "Routes and trips are ranked by modelled accessibility consequence only; ridership, cost, vehicle availability and equity weights are not included.",
            "The A1.7 full-day right-loop temporal profile is retained separately and remains hourly sampled.",
            "Hospital destinations are OSM features verified against the 2026-08-01 Ehime official medical registry.",
            "Population is a census-derived simplified 100 m allocation and is classification B.",
            "All route/trip outages are D stress-test assumptions, not damage forecasts.",
        ],
        repository=ROOT,
    )

    summary = {
        "stage": "A1.8",
        "status": "computed",
        "title": "大洲市 ぐるりんおおず Route / Trip Criticality",
        "classification": "C",
        "scenario_classification": "D",
        "analysis_date": ANALYSIS_DATE.isoformat(),
        "departure_time": "08:00:00",
        "temporal_window": {"start": "06:00", "end": "21:00", "step_minutes": 60, "slots": len(temporal_rows)},
        "gtfs": {
            "publisher": "大洲市",
            "feed_version": (feed.files.get("feed_info.txt") or [{}])[0].get("feed_version"),
            "feed_start_date": (feed.files.get("feed_info.txt") or [{}])[0].get("feed_start_date"),
            "feed_end_date": (feed.files.get("feed_info.txt") or [{}])[0].get("feed_end_date"),
            "stops": len(feed.files["stops.txt"]), "snapped_stops": len(stop_nodes),
            "routes": len(feed.files["routes.txt"]), "trips": len(feed.files["trips.txt"]),
            "active_routes": len(active_route_ids), "active_trips": len(active_trip_ids),
            "active_connections": len(connections),
        },
        "osm": {"walking_nodes": len(graph.nodes), "walking_edges": len(graph.edges), "hospital_destinations": len(facilities)},
        "official_registry": {"source_as_of": OFFICIAL_MEDICAL_AS_OF, **verification, "raw_workbook_published": False, "official_attributes_in_public_geojson": False},
        "population": {"source_rows": len(population_rows), "zones_in_envelope": len(zones), "population_in_envelope": round(sum(float(z["population"]) for z in zones), 4)},
        "transfer_network": {"max_walk_minutes": MAX_TRANSFER_WALK_MINUTES, "transfer_buffer_minutes": TRANSFER_BUFFER_MINUTES, "directed_edges": sum(len(e) for e in transfers.values()), "stops_with_outgoing_transfer": len(transfers)},
        "scenario": {"id": "ozu-clockwise-loop-unavailable", "disabled_route_ids": sorted(right_loop_routes), "disabled_route_names": [route_names[r] for r in sorted(right_loop_routes)]},
        "baseline": baseline,
        "disrupted": disrupted,
        "impact": reference_impact,
        "temporal_resilience": {
            "worst_affected_time": worst_affected["departure_time"],
            "worst_affected_population": worst_affected["impact"]["population_with_gt_1min_increase"],
            "worst_mean_degradation_time": worst_mean["departure_time"],
            "worst_mean_degradation_minutes": worst_mean["impact"]["mean_minutes_change"],
            "lowest_affected_time": lowest["departure_time"],
            "lowest_affected_population": lowest["impact"]["population_with_gt_1min_increase"],
        },
        "criticality": {
            "reference_time": "08:00",
            "method": "leave-one-out",
            "ranking_rule": "population_with_gt_1min_increase desc, mean_minutes_change desc, id asc",
            "routes_evaluated": len(route_ranking),
            "trips_evaluated": len(trip_ranking),
            "top_route": route_ranking[0],
            "top_trip": trip_ranking[0],
        },
        "provenance": provenance,
    }

    criticality = {
        "stage": "A1.8",
        "reference_time": "08:00",
        "method": "leave-one-out",
        "ranking_rule": summary["criticality"]["ranking_rule"],
        "route_ranking": route_ranking,
        "trip_ranking": trip_ranking,
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "criticality.json").write_text(json.dumps(criticality, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "temporal_profile.json").write_text(json.dumps({"stage": "A1.8", "source_stage": "A1.7", "rows": temporal_rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "stops.geojson").write_text(json.dumps(geojson_points(stops, ["stop_id", "name", "snap_km"]), ensure_ascii=False), encoding="utf-8")
    (output / "facilities.geojson").write_text(json.dumps(geojson_points(facilities, ["name", "amenity", "snap_km", "officially_verified", "verification_distance_km"]), ensure_ascii=False), encoding="utf-8")
    route_geojson = feed.route_geojson()
    for feature in route_geojson["features"]:
        feature["properties"]["route_name"] = route_names.get(feature["properties"]["route_id"])
    (output / "routes.geojson").write_text(json.dumps(route_geojson, ensure_ascii=False), encoding="utf-8")

    zone_features: list[dict[str, Any]] = []
    for zone in zones:
        zid = str(zone["zone_id"])
        before, after = baseline_minutes[zid], disrupted_minutes[zid]
        zone_features.append({
            "type": "Feature", "id": zid,
            "properties": {
                "zone_id": zid, "population": round(float(zone["population"]), 4),
                "baseline_minutes": None if not math.isfinite(before) else round(before, 2),
                "disrupted_minutes": None if not math.isfinite(after) else round(after, 2),
                "delta_minutes": None if not (math.isfinite(before) and math.isfinite(after)) else round(after - before, 2),
                "classification": "C",
            },
            "geometry": {"type": "Point", "coordinates": [zone["lon"], zone["lat"]]},
        })
    (output / "population_access.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": zone_features}, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "stage": "A1.8",
        "routes_evaluated": len(route_ranking),
        "trips_evaluated": len(trip_ranking),
        "top_route": route_ranking[0],
        "top_trip": trip_ranking[0],
    }, ensure_ascii=False, indent=2))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "a1_8")
    args = parser.parse_args()
    summary = build(args.output)
    return 0 if summary["criticality"]["routes_evaluated"] and summary["criticality"]["trips_evaluated"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
