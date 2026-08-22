"""A1.7: full-day temporal resilience for the verified Ozu accessibility model.

The reference map remains 08:00 for continuity with A1.6. In addition, A1.7
recomputes the same baseline and clockwise-route outage every hour from 06:00
to 21:00 and publishes aggregate temporal metrics. No time slot is selected or
suppressed based on whether it produces a visually interesting result.
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

REFERENCE_DEPARTURE_SECONDS = 8 * 3600
TEMPORAL_START_HOUR = 6
TEMPORAL_END_HOUR = 21
TEMPORAL_STEP_MINUTES = 60


def evaluate_at(
    *,
    departure_seconds: int,
    zones: list[dict[str, Any]],
    connections: list[dict[str, Any]],
    trip_routes: dict[str, str],
    stop_walk: dict[str, dict[str, float]],
    facility_walk_by_node: dict[str, float],
    stop_nodes: dict[str, str],
    disabled_routes: set[str],
    transfers: dict[str, list[dict[str, float | str]]],
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
            disabled_routes=disabled_routes,
            stop_transfers=transfers,
        )
    return values, summarize_population_access(zones, values)


def impact_metrics(
    zones: list[dict[str, Any]],
    baseline_minutes: dict[str, float],
    disrupted_minutes: dict[str, float],
    baseline: dict[str, float],
    disrupted: dict[str, float],
) -> dict[str, float]:
    affected = 0.0
    affected_5 = 0.0
    affected_10 = 0.0
    for zone in zones:
        zone_id = str(zone["zone_id"])
        before = baseline_minutes.get(zone_id, math.inf)
        after = disrupted_minutes.get(zone_id, math.inf)
        if not (math.isfinite(before) and math.isfinite(after)):
            continue
        delta = after - before
        pop = float(zone["population"])
        if delta > 1.0:
            affected += pop
        if delta > 5.0:
            affected_5 += pop
        if delta > 10.0:
            affected_10 += pop
    return {
        "population_with_gt_1min_increase": round(affected, 4),
        "population_with_gt_5min_increase": round(affected_5, 4),
        "population_with_gt_10min_increase": round(affected_10, 4),
        "accessibility_loss_30min_population": round(
            baseline["reachable_30min"] - disrupted["reachable_30min"], 4
        ),
        "accessibility_loss_60min_population": round(
            baseline["reachable_60min"] - disrupted["reachable_60min"], 4
        ),
        "mean_minutes_change": round(
            disrupted["population_weighted_mean_minutes"]
            - baseline["population_weighted_mean_minutes"],
            3,
        ),
    }


def time_label(seconds: int) -> str:
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}"


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

    osm_hospitals = extract_facilities(osm, allowed={"hospital"})
    official = official_hospitals(official_payload, bbox)
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
            "id": row["stop_id"],
            "stop_id": row["stop_id"],
            "name": row["stop_name"],
            "lat": float(row["stop_lat"]),
            "lon": float(row["stop_lon"]),
        }
        for row in feed.files["stops.txt"]
    ]
    stop_nodes, stops = snap_points(stops, index, max_snap_km=0.5)
    if len(stop_nodes) != len(feed.files["stops.txt"]):
        raise ValueError("A1.7 requires all GTFS stops to snap to the walking network")

    zones = zones_to_nodes(population_zones(population_rows, bbox), index)
    if not zones:
        raise ValueError("no population zones available")

    facility_walk = min_walk_minutes_to_facility(graph, facility_nodes.values())
    stop_walk = stop_walk_times(graph, stop_nodes)
    transfers = stop_transfer_edges(
        stop_walk,
        stop_nodes,
        max_walk_minutes=MAX_TRANSFER_WALK_MINUTES,
        transfer_buffer_minutes=TRANSFER_BUFFER_MINUTES,
    )
    if not transfers:
        raise ValueError("walking transfer graph is empty")

    connections = feed.connections(ANALYSIS_DATE)
    if not connections:
        raise ValueError(f"GTFS has no connections on {ANALYSIS_DATE}")
    connections = sorted(
        connections, key=lambda item: (item["departure_seconds"], item["arrival_seconds"])
    )
    trip_routes = {row["trip_id"]: row["route_id"] for row in feed.files["trips.txt"]}
    route_names = {
        row["route_id"]: row.get("route_long_name", row["route_id"])
        for row in feed.files["routes.txt"]
    }
    disabled_routes = {
        route_id for route_id, route_name in route_names.items() if "右回り" in route_name
    }
    if not disabled_routes:
        raise ValueError("clockwise routes were not found")

    temporal_rows: list[dict[str, Any]] = []
    reference_baseline_minutes: dict[str, float] | None = None
    reference_disrupted_minutes: dict[str, float] | None = None
    reference_baseline: dict[str, float] | None = None
    reference_disrupted: dict[str, float] | None = None

    start = TEMPORAL_START_HOUR * 3600
    end = TEMPORAL_END_HOUR * 3600
    step = TEMPORAL_STEP_MINUTES * 60
    for departure_seconds in range(start, end + 1, step):
        baseline_minutes, baseline = evaluate_at(
            departure_seconds=departure_seconds,
            zones=zones,
            connections=connections,
            trip_routes=trip_routes,
            stop_walk=stop_walk,
            facility_walk_by_node=facility_walk,
            stop_nodes=stop_nodes,
            disabled_routes=set(),
            transfers=transfers,
        )
        disrupted_minutes, disrupted = evaluate_at(
            departure_seconds=departure_seconds,
            zones=zones,
            connections=connections,
            trip_routes=trip_routes,
            stop_walk=stop_walk,
            facility_walk_by_node=facility_walk,
            stop_nodes=stop_nodes,
            disabled_routes=disabled_routes,
            transfers=transfers,
        )
        impact = impact_metrics(zones, baseline_minutes, disrupted_minutes, baseline, disrupted)
        temporal_rows.append(
            {
                "departure_time": time_label(departure_seconds),
                "departure_seconds": departure_seconds,
                "baseline": baseline,
                "disrupted": disrupted,
                "impact": impact,
            }
        )
        if departure_seconds == REFERENCE_DEPARTURE_SECONDS:
            reference_baseline_minutes = baseline_minutes
            reference_disrupted_minutes = disrupted_minutes
            reference_baseline = baseline
            reference_disrupted = disrupted

    if reference_baseline_minutes is None or reference_disrupted_minutes is None:
        raise ValueError("08:00 reference slot was not computed")
    assert reference_baseline is not None and reference_disrupted is not None

    worst_affected = max(
        temporal_rows,
        key=lambda row: float(row["impact"]["population_with_gt_1min_increase"]),
    )
    worst_mean = max(
        temporal_rows,
        key=lambda row: float(row["impact"]["mean_minutes_change"]),
    )
    best_affected = min(
        temporal_rows,
        key=lambda row: float(row["impact"]["population_with_gt_1min_increase"]),
    )

    provenance = make_provenance(
        "a1-7-ozu-temporal-resilience",
        "C",
        "minimal-multimodal-v0.1.7",
        [
            {
                "dataset_id": "ozu_gururin_gtfs_20260401",
                "source": GTFS_LANDING,
                "classification": "A",
                "license": "CC BY 4.0",
            },
            {
                "dataset_id": "ozu_population_100m_2020",
                "source": POP_LANDING,
                "classification": "B",
                "license": "CC BY",
            },
            {
                "dataset_id": "osm_ozu_gtfs_envelope",
                "source": "https://www.openstreetmap.org/copyright",
                "classification": "B",
                "license": "ODbL 1.0",
            },
            {
                "dataset_id": "ehime_medical_basic_information_20260801",
                "source": OFFICIAL_MEDICAL_LANDING,
                "classification": "A",
                "license": "official website publication; redistribution not asserted",
                "usage": "transient verification only; raw rows are not published",
            },
        ],
        {
            "analysis_date": ANALYSIS_DATE.isoformat(),
            "reference_departure_time": "08:00:00",
            "temporal_start": f"{TEMPORAL_START_HOUR:02d}:00",
            "temporal_end": f"{TEMPORAL_END_HOUR:02d}:00",
            "temporal_step_minutes": TEMPORAL_STEP_MINUTES,
            "walking_speed_kmh": 4.8,
            "max_access_walk_minutes": 20,
            "max_transfer_walk_minutes": MAX_TRANSFER_WALK_MINUTES,
            "transfer_buffer_minutes": TRANSFER_BUFFER_MINUTES,
            "official_registry_as_of": OFFICIAL_MEDICAL_AS_OF,
            "disabled_routes": sorted(disabled_routes),
        },
        scenario_id="ozu-clockwise-loop-unavailable",
        limitations=[
            "A1.7 covers the Gururin Ozu service envelope, not all Ehime Prefecture.",
            "The full-day profile is sampled hourly from 06:00 through 21:00; it is not a continuous-time integral.",
            "Stop-to-stop transfers use OSM pedestrian-network shortest paths up to 10 walking minutes plus a fixed 1-minute transfer buffer.",
            "Hospital destinations are OSM features verified against the 2026-08-01 Ehime official medical registry.",
            "Population is a census-derived simplified 100 m allocation and is classification B.",
            "The clockwise-route outage is a user-defined stress-test assumption (D), not a damage forecast.",
            "GTFS has no shapes.txt; public route geometry uses stop-order polylines.",
        ],
        repository=ROOT,
    )

    reference_impact = impact_metrics(
        zones,
        reference_baseline_minutes,
        reference_disrupted_minutes,
        reference_baseline,
        reference_disrupted,
    )
    summary = {
        "stage": "A1.7",
        "status": "computed",
        "title": "大洲市 ぐるりんおおず 終日時間帯レジリエンス",
        "classification": "C",
        "scenario_classification": "D",
        "analysis_date": ANALYSIS_DATE.isoformat(),
        "departure_time": "08:00:00",
        "temporal_window": {
            "start": f"{TEMPORAL_START_HOUR:02d}:00",
            "end": f"{TEMPORAL_END_HOUR:02d}:00",
            "step_minutes": TEMPORAL_STEP_MINUTES,
            "slots": len(temporal_rows),
        },
        "gtfs": {
            "publisher": "大洲市",
            "feed_version": (feed.files.get("feed_info.txt") or [{}])[0].get("feed_version"),
            "feed_start_date": (feed.files.get("feed_info.txt") or [{}])[0].get("feed_start_date"),
            "feed_end_date": (feed.files.get("feed_info.txt") or [{}])[0].get("feed_end_date"),
            "stops": len(feed.files["stops.txt"]),
            "snapped_stops": len(stop_nodes),
            "routes": len(feed.files["routes.txt"]),
            "trips": len(feed.files["trips.txt"]),
            "active_connections": len(connections),
        },
        "osm": {
            "walking_nodes": len(graph.nodes),
            "walking_edges": len(graph.edges),
            "hospital_destinations": len(facilities),
            "hospital_names": sorted(str(item.get("name", "hospital")) for item in facilities),
        },
        "official_registry": {
            "source_as_of": OFFICIAL_MEDICAL_AS_OF,
            **verification,
            "raw_workbook_published": False,
            "official_attributes_in_public_geojson": False,
        },
        "population": {
            "source_rows": len(population_rows),
            "zones_in_envelope": len(zones),
            "population_in_envelope": round(sum(float(z["population"]) for z in zones), 4),
        },
        "transfer_network": {
            "max_walk_minutes": MAX_TRANSFER_WALK_MINUTES,
            "transfer_buffer_minutes": TRANSFER_BUFFER_MINUTES,
            "directed_edges": sum(len(edges) for edges in transfers.values()),
            "stops_with_outgoing_transfer": len(transfers),
        },
        "scenario": {
            "id": "ozu-clockwise-loop-unavailable",
            "disabled_route_ids": sorted(disabled_routes),
            "disabled_route_names": [route_names[r] for r in sorted(disabled_routes)],
        },
        "baseline": reference_baseline,
        "disrupted": reference_disrupted,
        "impact": reference_impact,
        "temporal_resilience": {
            "worst_affected_time": worst_affected["departure_time"],
            "worst_affected_population": worst_affected["impact"]["population_with_gt_1min_increase"],
            "worst_mean_degradation_time": worst_mean["departure_time"],
            "worst_mean_degradation_minutes": worst_mean["impact"]["mean_minutes_change"],
            "lowest_affected_time": best_affected["departure_time"],
            "lowest_affected_population": best_affected["impact"]["population_with_gt_1min_increase"],
        },
        "provenance": provenance,
    }

    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "temporal_profile.json").write_text(
        json.dumps({"stage": "A1.7", "rows": temporal_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output / "stops.geojson").write_text(
        json.dumps(geojson_points(stops, ["stop_id", "name", "snap_km"]), ensure_ascii=False),
        encoding="utf-8",
    )
    (output / "facilities.geojson").write_text(
        json.dumps(
            geojson_points(
                facilities,
                ["name", "amenity", "snap_km", "officially_verified", "verification_distance_km"],
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    route_geojson = feed.route_geojson()
    for feature in route_geojson["features"]:
        feature["properties"]["route_name"] = route_names.get(feature["properties"]["route_id"])
    (output / "routes.geojson").write_text(json.dumps(route_geojson, ensure_ascii=False), encoding="utf-8")

    zone_features: list[dict[str, Any]] = []
    for zone in zones:
        zone_id = str(zone["zone_id"])
        before = reference_baseline_minutes[zone_id]
        after = reference_disrupted_minutes[zone_id]
        zone_features.append(
            {
                "type": "Feature",
                "id": zone_id,
                "properties": {
                    "zone_id": zone_id,
                    "population": round(float(zone["population"]), 4),
                    "baseline_minutes": None if not math.isfinite(before) else round(before, 2),
                    "disrupted_minutes": None if not math.isfinite(after) else round(after, 2),
                    "delta_minutes": None if not (math.isfinite(before) and math.isfinite(after)) else round(after - before, 2),
                    "classification": "C",
                },
                "geometry": {"type": "Point", "coordinates": [zone["lon"], zone["lat"]]},
            }
        )
    (output / "population_access.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": zone_features}, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps({
        "stage": "A1.7",
        "slots": len(temporal_rows),
        "temporal_resilience": summary["temporal_resilience"],
        "reference_impact": reference_impact,
    }, ensure_ascii=False, indent=2))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "a1_7")
    args = parser.parse_args()
    summary = build(args.output)
    return 0 if summary["temporal_window"]["slots"] >= 2 else 2


if __name__ == "__main__":
    raise SystemExit(main())
