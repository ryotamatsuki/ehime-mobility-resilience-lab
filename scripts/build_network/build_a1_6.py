"""A1.6: add stop-to-stop walking transfers to the verified Ozu A1 model.

A1.6 keeps the A1.5 source and hospital-verification boundary unchanged, then
adds explicit walking transfer edges between GTFS stops using the OSM pedestrian
network. The build computes both a same-input no-transfer counterfactual and the
new transfer-enabled model so that model improvement is auditable.
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
    DEPARTURE_SECONDS,
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

MAX_TRANSFER_WALK_MINUTES = 10.0
TRANSFER_BUFFER_MINUTES = 1.0


def evaluate(
    *,
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
        values[str(zone["zone_id"])] = earliest_arrival_minutes(
            zone_node=str(zone["node"]),
            departure_seconds=DEPARTURE_SECONDS,
            connections=connections,
            trip_routes=trip_routes,
            stop_walk=stop_walk,
            facility_walk_by_node=facility_walk_by_node,
            stop_nodes=stop_nodes,
            disabled_routes=disabled_routes,
            stop_transfers=transfers,
        )
    return values, summarize_population_access(zones, values)


def compare_transfer_model(
    zones: list[dict[str, Any]],
    without_transfer: dict[str, float],
    with_transfer: dict[str, float],
    without_summary: dict[str, float],
    with_summary: dict[str, float],
) -> dict[str, float | int]:
    improved_population = 0.0
    improved_zones = 0
    newly_reachable_population = 0.0
    finite_improvements: list[float] = []
    for zone in zones:
        zone_id = str(zone["zone_id"])
        old = without_transfer.get(zone_id, math.inf)
        new = with_transfer.get(zone_id, math.inf)
        if math.isfinite(old) and not math.isfinite(new):
            raise ValueError("walking transfers worsened a finite journey to unreachable")
        if math.isfinite(old) and math.isfinite(new) and new > old + 1e-6:
            raise ValueError("walking transfers increased an earliest-arrival result")
        if (not math.isfinite(old) and math.isfinite(new)) or (
            math.isfinite(old) and math.isfinite(new) and new < old - 0.01
        ):
            improved_population += float(zone["population"])
            improved_zones += 1
        if not math.isfinite(old) and math.isfinite(new):
            newly_reachable_population += float(zone["population"])
        if math.isfinite(old) and math.isfinite(new) and old > new:
            finite_improvements.append(old - new)

    old_mean = float(without_summary["population_weighted_mean_minutes"])
    new_mean = float(with_summary["population_weighted_mean_minutes"])
    return {
        "improved_zones": improved_zones,
        "improved_population": round(improved_population, 4),
        "newly_reachable_population": round(newly_reachable_population, 4),
        "population_weighted_mean_reduction_minutes": round(old_mean - new_mean, 3),
        "max_finite_reduction_minutes": round(max(finite_improvements, default=0.0), 3),
    }


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
    if not official:
        raise ValueError("official medical registry has no active hospitals in A1 envelope")
    if not verified_hospitals:
        raise ValueError("no OSM hospital could be verified against the official registry")

    facility_nodes, facilities = snap_points(
        [dict(item, id=item["id"]) for item in verified_hospitals],
        index,
        max_snap_km=0.5,
    )
    if not facility_nodes:
        raise ValueError("no official-verified OSM hospital snapped to the walking network")

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
    if len(stop_nodes) < max(1, int(len(feed.files["stops.txt"]) * 0.9)):
        raise ValueError("fewer than 90% of GTFS stops snapped to walking network")

    zones = zones_to_nodes(population_zones(population_rows, bbox), index)
    if not zones:
        raise ValueError("no population zones available in A1.6 service envelope")

    facility_walk = min_walk_minutes_to_facility(graph, facility_nodes.values())
    stop_walk = stop_walk_times(graph, stop_nodes)
    transfers = stop_transfer_edges(
        stop_walk,
        stop_nodes,
        max_walk_minutes=MAX_TRANSFER_WALK_MINUTES,
        transfer_buffer_minutes=TRANSFER_BUFFER_MINUTES,
    )
    transfer_edge_count = sum(len(edges) for edges in transfers.values())
    if transfer_edge_count < 1:
        raise ValueError("A1.6 generated no stop-to-stop walking transfer edges")

    connections = feed.connections(ANALYSIS_DATE)
    if not connections:
        raise ValueError(f"GTFS has no connections on {ANALYSIS_DATE}")

    trip_routes = {row["trip_id"]: row["route_id"] for row in feed.files["trips.txt"]}
    route_names = {
        row["route_id"]: row.get("route_long_name", row["route_id"])
        for row in feed.files["routes.txt"]
    }
    disabled_routes = {
        route_id for route_id, route_name in route_names.items() if "右回り" in route_name
    }
    if not disabled_routes:
        raise ValueError("clockwise stress-test routes were not found")

    no_transfer_baseline_minutes, no_transfer_baseline = evaluate(
        zones=zones,
        connections=connections,
        trip_routes=trip_routes,
        stop_walk=stop_walk,
        facility_walk_by_node=facility_walk,
        stop_nodes=stop_nodes,
        disabled_routes=set(),
        transfers={},
    )
    no_transfer_disrupted_minutes, no_transfer_disrupted = evaluate(
        zones=zones,
        connections=connections,
        trip_routes=trip_routes,
        stop_walk=stop_walk,
        facility_walk_by_node=facility_walk,
        stop_nodes=stop_nodes,
        disabled_routes=disabled_routes,
        transfers={},
    )
    baseline_minutes, baseline = evaluate(
        zones=zones,
        connections=connections,
        trip_routes=trip_routes,
        stop_walk=stop_walk,
        facility_walk_by_node=facility_walk,
        stop_nodes=stop_nodes,
        disabled_routes=set(),
        transfers=transfers,
    )
    disrupted_minutes, disrupted = evaluate(
        zones=zones,
        connections=connections,
        trip_routes=trip_routes,
        stop_walk=stop_walk,
        facility_walk_by_node=facility_walk,
        stop_nodes=stop_nodes,
        disabled_routes=disabled_routes,
        transfers=transfers,
    )

    transfer_effect_baseline = compare_transfer_model(
        zones,
        no_transfer_baseline_minutes,
        baseline_minutes,
        no_transfer_baseline,
        baseline,
    )
    transfer_effect_disrupted = compare_transfer_model(
        zones,
        no_transfer_disrupted_minutes,
        disrupted_minutes,
        no_transfer_disrupted,
        disrupted,
    )

    affected_population = sum(
        float(zone["population"])
        for zone in zones
        if disrupted_minutes[str(zone["zone_id"])]
        > baseline_minutes[str(zone["zone_id"])] + 1.0
    )
    loss_30 = baseline["reachable_30min"] - disrupted["reachable_30min"]
    loss_60 = baseline["reachable_60min"] - disrupted["reachable_60min"]

    transfer_walk_values = [
        float(edge["walk_minutes"])
        for edges in transfers.values()
        for edge in edges
    ]
    transfer_network = {
        "max_walk_minutes": MAX_TRANSFER_WALK_MINUTES,
        "transfer_buffer_minutes": TRANSFER_BUFFER_MINUTES,
        "directed_edges": transfer_edge_count,
        "stops_with_outgoing_transfer": len(transfers),
        "candidate_stop_pairs": len(stop_nodes) * max(0, len(stop_nodes) - 1),
        "mean_network_walk_minutes": round(
            sum(transfer_walk_values) / len(transfer_walk_values), 3
        ),
        "max_generated_network_walk_minutes": round(max(transfer_walk_values), 3),
        "recursive_walking_transfer_chaining": False,
    }

    provenance = make_provenance(
        "a1-6-ozu-walking-transfer-accessibility",
        "C",
        "minimal-multimodal-v0.1.6",
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
            "departure_time": "08:00:00",
            "walking_speed_kmh": 4.8,
            "max_access_walk_minutes": 20,
            "max_transfer_walk_minutes": MAX_TRANSFER_WALK_MINUTES,
            "transfer_buffer_minutes": TRANSFER_BUFFER_MINUTES,
            "recursive_walking_transfer_chaining": False,
            "analysis_extent": "GTFS stop bbox + 0.02 degrees",
            "facility_types": ["official-registry-verified OSM hospital"],
            "official_registry_as_of": OFFICIAL_MEDICAL_AS_OF,
            "disabled_routes": sorted(disabled_routes),
        },
        scenario_id="ozu-clockwise-loop-unavailable",
        limitations=[
            "A1.6 covers the Gururin Ozu service envelope, not all Ehime Prefecture.",
            "Stop-to-stop transfers use OSM pedestrian-network shortest paths up to 10 walking minutes plus a fixed 1-minute transfer buffer.",
            "Walking-transfer edges are direct pairwise edges and are not recursively chained; this prevents short-hop chaining from bypassing the configured transfer limit.",
            "GTFS pathways, station-internal accessibility, wheelchair constraints, crossing delay and slope are not yet modelled.",
            "Hospital destinations are OSM features verified against the 2026-08-01 Ehime official medical registry; unmatched official hospitals are not added because the official workbook is not republished.",
            "The official medical workbook is downloaded transiently for verification; raw rows, official identifiers, addresses and coordinates are not included in public artifacts.",
            "Population is a census-derived simplified 100 m allocation and is classification B.",
            "The clockwise-route outage is a user-defined stress-test assumption (D), not a damage forecast.",
            "GTFS has no shapes.txt; public route geometry therefore uses stop-order polylines.",
        ],
        repository=ROOT,
    )

    summary = {
        "stage": "A1.6",
        "status": "computed",
        "title": "大洲市 ぐるりんおおず 徒歩乗換対応 病院Accessibility Stress Test",
        "classification": "C",
        "scenario_classification": "D",
        "analysis_date": ANALYSIS_DATE.isoformat(),
        "departure_time": "08:00:00",
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
            "population_in_envelope": round(
                sum(float(zone["population"]) for zone in zones), 4
            ),
        },
        "transfer_network": transfer_network,
        "same_input_no_transfer": {
            "baseline": no_transfer_baseline,
            "disrupted": no_transfer_disrupted,
        },
        "transfer_model_effect": {
            "baseline": transfer_effect_baseline,
            "disrupted": transfer_effect_disrupted,
        },
        "scenario": {
            "id": "ozu-clockwise-loop-unavailable",
            "disabled_route_ids": sorted(disabled_routes),
            "disabled_route_names": [route_names[route_id] for route_id in sorted(disabled_routes)],
        },
        "baseline": baseline,
        "disrupted": disrupted,
        "impact": {
            "accessibility_loss_30min_population": round(loss_30, 4),
            "accessibility_loss_60min_population": round(loss_60, 4),
            "population_with_gt_1min_increase": round(affected_population, 4),
            "mean_minutes_change": round(
                disrupted["population_weighted_mean_minutes"]
                - baseline["population_weighted_mean_minutes"],
                3,
            ),
        },
        "provenance": provenance,
    }

    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
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
    (output / "routes.geojson").write_text(
        json.dumps(route_geojson, ensure_ascii=False), encoding="utf-8"
    )

    zone_features: list[dict[str, Any]] = []
    for zone in zones:
        zone_id = str(zone["zone_id"])
        before = baseline_minutes[zone_id]
        after = disrupted_minutes[zone_id]
        old_before = no_transfer_baseline_minutes[zone_id]
        old_after = no_transfer_disrupted_minutes[zone_id]
        zone_features.append(
            {
                "type": "Feature",
                "id": zone_id,
                "properties": {
                    "zone_id": zone_id,
                    "population": round(float(zone["population"]), 4),
                    "baseline_minutes": None if not math.isfinite(before) else round(before, 2),
                    "disrupted_minutes": None if not math.isfinite(after) else round(after, 2),
                    "delta_minutes": None
                    if not (math.isfinite(before) and math.isfinite(after))
                    else round(after - before, 2),
                    "baseline_no_transfer_minutes": None
                    if not math.isfinite(old_before)
                    else round(old_before, 2),
                    "disrupted_no_transfer_minutes": None
                    if not math.isfinite(old_after)
                    else round(old_after, 2),
                    "classification": "C",
                },
                "geometry": {"type": "Point", "coordinates": [zone["lon"], zone["lat"]]},
            }
        )
    (output / "population_access.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": zone_features}, ensure_ascii=False),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "stage": summary["stage"],
                "status": summary["status"],
                "gtfs_stops": summary["gtfs"]["stops"],
                "population_zones": summary["population"]["zones_in_envelope"],
                "hospital_destinations": summary["osm"]["hospital_destinations"],
                "transfer_network": summary["transfer_network"],
                "transfer_model_effect": summary["transfer_model_effect"],
                "impact": summary["impact"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "a1_6")
    args = parser.parse_args()
    summary = build(args.output)
    if summary["gtfs"]["snapped_stops"] < 1:
        return 2
    if summary["population"]["zones_in_envelope"] < 1:
        return 3
    if summary["osm"]["hospital_destinations"] < 1:
        return 4
    if summary["official_registry"]["verified_osm_hospitals"] < 1:
        return 5
    if summary["transfer_network"]["directed_edges"] < 1:
        return 6
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
