"""A1.9: official Ozu shelter accessibility.

A1.8 temporal resilience and route/trip criticality are regenerated first and
preserved. A1.9 then adds three official destination classes from Ozu City's CC
BY 4.0 shelter workbook: designated emergency evacuation places, designated
general shelters and designated welfare shelters.

The workbook has no coordinates. Facility geometry is therefore accepted only
when an OSM named feature in the current GTFS analysis envelope passes a strict,
unambiguous name match. Unmatched/ambiguous official records are excluded and
reported; no hidden geocoder or guessed point is used.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.parse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from accessibility.multimodal import (
    CoordinateIndex,
    min_walk_minutes_to_facility,
    stop_transfer_edges,
    stop_walk_times,
    summarize_population_access,
    walking_graph_from_overpass,
)
from accessibility.official_shelters import (
    match_official_shelters,
    official_shelters,
    osm_named_candidates,
)
from common.provenance import make_provenance
from scripts.build_network.build_a1_1 import (
    ANALYSIS_DATE,
    GTFS_LANDING,
    GTFS_URL,
    OVERPASS_URL,
    POP_LANDING,
    POP_URL,
    fetch,
    first_csv_rows,
    gtfs_bbox,
    load_feed,
    population_zones,
    snap_points,
    zones_to_nodes,
)
from scripts.build_network.build_a1_5 import OFFICIAL_MEDICAL_LANDING
from scripts.build_network.build_a1_6 import MAX_TRANSFER_WALK_MINUTES, TRANSFER_BUFFER_MINUTES
from scripts.build_network.build_a1_7 import REFERENCE_DEPARTURE_SECONDS
from scripts.build_network.build_a1_8 import build as build_a1_8, evaluate_at, impact_metrics

SHELTER_URL = "https://www.city.ozu.ehime.jp/uploaded/attachment/47130.xlsx"
SHELTER_LANDING = "https://www.city.ozu.ehime.jp/site/opendata/31903.html"
SHELTER_AS_OF = "2026-04-01"
SHELTER_KINDS = ("emergency", "general", "welfare")
SHELTER_KIND_LABELS = {
    "emergency": "指定緊急避難場所",
    "general": "指定一般避難所",
    "welfare": "指定福祉避難所",
}


def fetch_osm_for_shelters(bbox: tuple[float, float, float, float]) -> dict[str, Any]:
    """Fetch walking roads plus named public/facility features in the A1 envelope."""
    south, west, north, east = bbox
    box = f"{south:.6f},{west:.6f},{north:.6f},{east:.6f}"
    query = f"""
[out:json][timeout:90];
way["highway"]({box});
out body geom;
(
  nwr["name"]["amenity"]({box});
  nwr["name"]["leisure"]({box});
  nwr["name"]["building"]({box});
  nwr["name"]["office"="government"]({box});
  nwr["name"]["tourism"]({box});
);
out body center;
""".strip()
    payload = fetch(
        OVERPASS_URL,
        data=urllib.parse.urlencode({"data": query}).encode(),
        timeout=120,
    )
    return json.loads(payload.decode("utf-8"))


def _public_shelter_feature(item: dict[str, Any]) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "shelter_id": item["official_id"],
        "kind": item["kind"],
        "kind_label": SHELTER_KIND_LABELS[item["kind"]],
        "name": item["name"],
        "address": item.get("address") or "",
        "capacity": item.get("capacity"),
        "location_source": item.get("location_source"),
        "location_match_method": item.get("location_match_method"),
        "location_match_score": item.get("location_match_score"),
        "osm_name": item.get("osm_name"),
        "snap_km": item.get("snap_km"),
        "classification": "A attributes + B geometry",
    }
    if item["kind"] == "emergency":
        properties["hazards"] = item.get("hazards") or {}
    if item["kind"] == "welfare":
        properties["target_users"] = item.get("target_users") or ""
    return {
        "type": "Feature",
        "id": item["official_id"],
        "properties": properties,
        "geometry": {"type": "Point", "coordinates": [item["lon"], item["lat"]]},
    }


def build(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)

    # Preserve all validated predecessor outputs first.
    predecessor = build_a1_8(output)

    feed = load_feed(fetch(GTFS_URL))
    bbox = gtfs_bbox(feed)
    population_rows = first_csv_rows(fetch(POP_URL))
    osm = fetch_osm_for_shelters(bbox)
    official_payload = fetch(SHELTER_URL)

    graph, node_coordinates = walking_graph_from_overpass(osm)
    graph_errors = graph.validate()
    if graph_errors:
        raise ValueError("A1.9 walking graph invalid: " + "; ".join(graph_errors[:20]))
    index = CoordinateIndex(node_coordinates)

    official = official_shelters(official_payload)
    expected_counts = {"emergency": 60, "general": 96, "welfare": 20}
    for kind, expected in expected_counts.items():
        if len(official.get(kind, [])) != expected:
            raise ValueError(
                f"official shelter row count changed for {kind}: expected {expected}, got {len(official.get(kind, []))}"
            )

    candidates = osm_named_candidates(osm)
    matched, matching_stats = match_official_shelters(official, candidates)

    # Stops / population use the exact A1 envelope and walking graph.
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
        raise ValueError("A1.9 requires all GTFS stops to snap")
    zones = zones_to_nodes(population_zones(population_rows, bbox), index)
    if not zones:
        raise ValueError("A1.9 has no population zones")
    stop_walk = stop_walk_times(graph, stop_nodes)
    transfers = stop_transfer_edges(
        stop_walk,
        stop_nodes,
        max_walk_minutes=MAX_TRANSFER_WALK_MINUTES,
        transfer_buffer_minutes=TRANSFER_BUFFER_MINUTES,
    )
    if not transfers:
        raise ValueError("A1.9 walking transfer graph is empty")

    connections = sorted(
        feed.connections(ANALYSIS_DATE),
        key=lambda item: (item["departure_seconds"], item["arrival_seconds"]),
    )
    trip_rows = {str(row["trip_id"]): row for row in feed.files["trips.txt"]}
    trip_routes = {trip_id: str(row["route_id"]) for trip_id, row in trip_rows.items()}
    route_rows = {str(row["route_id"]): row for row in feed.files["routes.txt"]}
    route_names = {
        route_id: row.get("route_long_name") or row.get("route_short_name") or route_id
        for route_id, row in route_rows.items()
    }
    active_trip_ids = sorted({str(connection["trip_id"]) for connection in connections})
    active_route_ids = sorted({trip_routes[trip_id] for trip_id in active_trip_ids})
    right_loop_routes = {route_id for route_id in active_route_ids if "右回り" in route_names.get(route_id, "")}
    if not right_loop_routes:
        raise ValueError("A1.9 clockwise reference outage route not found")

    usable: dict[str, list[dict[str, Any]]] = {}
    facility_nodes_by_kind: dict[str, dict[str, str]] = {}
    for kind in SHELTER_KINDS:
        nodes, snapped = snap_points(
            [dict(item, id=item["official_id"]) for item in matched.get(kind, [])],
            index,
            max_snap_km=0.5,
        )
        usable[kind] = snapped
        facility_nodes_by_kind[kind] = nodes
        matching_stats["by_kind"][kind]["snapped_records"] = len(snapped)
        matching_stats["by_kind"][kind]["matched_but_unsnapped"] = len(matched.get(kind, [])) - len(snapped)
        if not snapped:
            raise ValueError(f"A1.9 has no strictly matched/snapped {kind} shelter in the GTFS envelope")

    access_by_kind: dict[str, Any] = {}
    zone_access: dict[str, dict[str, float]] = {str(zone["zone_id"]): {} for zone in zones}
    for kind in SHELTER_KINDS:
        facility_walk = min_walk_minutes_to_facility(graph, facility_nodes_by_kind[kind].values())
        baseline_minutes, baseline = evaluate_at(
            departure_seconds=REFERENCE_DEPARTURE_SECONDS,
            zones=zones,
            connections=connections,
            trip_routes=trip_routes,
            stop_walk=stop_walk,
            facility_walk_by_node=facility_walk,
            stop_nodes=stop_nodes,
            transfers=transfers,
        )
        disrupted_minutes, disrupted = evaluate_at(
            departure_seconds=REFERENCE_DEPARTURE_SECONDS,
            zones=zones,
            connections=connections,
            trip_routes=trip_routes,
            stop_walk=stop_walk,
            facility_walk_by_node=facility_walk,
            stop_nodes=stop_nodes,
            transfers=transfers,
            disabled_routes=right_loop_routes,
        )
        impact = impact_metrics(zones, baseline_minutes, disrupted_minutes, baseline, disrupted)
        access_by_kind[kind] = {
            "kind_label": SHELTER_KIND_LABELS[kind],
            "official_records_citywide": len(official[kind]),
            "osm_matched_in_analysis_envelope": len(matched[kind]),
            "usable_destinations": len(usable[kind]),
            "baseline": baseline,
            "disrupted": disrupted,
            "impact": impact,
        }
        for zone in zones:
            zone_id = str(zone["zone_id"])
            zone_access[zone_id][f"{kind}_baseline_minutes"] = baseline_minutes[zone_id]
            zone_access[zone_id][f"{kind}_disrupted_minutes"] = disrupted_minutes[zone_id]

    provenance = make_provenance(
        "a1-9-ozu-shelter-accessibility",
        "C",
        "minimal-multimodal-v0.1.9",
        [
            {"dataset_id": "ozu_gururin_gtfs_20260401", "source": GTFS_LANDING, "classification": "A", "license": "CC BY 4.0"},
            {"dataset_id": "ozu_shelters_20260401", "source": SHELTER_LANDING, "classification": "A", "license": "CC BY 4.0"},
            {"dataset_id": "ozu_population_100m_2020", "source": POP_LANDING, "classification": "B", "license": "CC BY"},
            {"dataset_id": "osm_ozu_gtfs_envelope", "source": "https://www.openstreetmap.org/copyright", "classification": "B", "license": "ODbL 1.0"},
            {"dataset_id": "ehime_medical_registry_verification", "source": OFFICIAL_MEDICAL_LANDING, "classification": "A", "license": "official website publication; redistribution not asserted", "usage": "predecessor hospital verification only"},
        ],
        {
            "analysis_date": ANALYSIS_DATE.isoformat(),
            "reference_time": "08:00:00",
            "walking_speed_kmh": 4.8,
            "max_access_walk_minutes": 20,
            "max_transfer_walk_minutes": MAX_TRANSFER_WALK_MINUTES,
            "transfer_buffer_minutes": TRANSFER_BUFFER_MINUTES,
            "shelter_source_as_of": SHELTER_AS_OF,
            "shelter_location_gate": "unambiguous OSM named-feature match; no geocoder",
            "shelter_match_min_score": 0.90,
            "shelter_match_ambiguity_margin": 0.03,
        },
        scenario_id="ozu-clockwise-loop-unavailable-shelter-access",
        limitations=[
            "Official Ozu shelter records contain no coordinates; A1.9 uses only unambiguously name-matched OSM geometry inside the current GTFS analysis envelope.",
            "Unmatched or ambiguous official shelters are excluded from accessibility calculations and reported in matching QA; they are not silently geocoded.",
            "Shelter accessibility therefore measures access to the verified subset in the current analysis envelope, not all citywide shelters.",
            "The right-loop outage is a D stress-test assumption, not a disaster damage forecast.",
            "Population is a census-derived simplified 100 m allocation (B).",
            "A1.8 route/trip criticality and A1.7 hourly temporal resilience remain predecessor analyses and are preserved unchanged.",
        ],
        repository=ROOT,
    )

    summary = dict(predecessor)
    summary.update(
        {
            "stage": "A1.9",
            "title": "大洲市 避難所 Accessibility",
            "provenance": provenance,
            "shelter_registry": {
                "source_as_of": SHELTER_AS_OF,
                "license": "CC BY 4.0",
                "citywide_counts": expected_counts,
                "location_source": "OpenStreetMap named features (B)",
                "matching": matching_stats,
                "raw_workbook_published": False,
            },
            "shelter_accessibility": access_by_kind,
        }
    )
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    shelter_features = [
        _public_shelter_feature(item)
        for kind in SHELTER_KINDS
        for item in usable[kind]
    ]
    (output / "shelters.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": shelter_features}, ensure_ascii=False),
        encoding="utf-8",
    )

    zone_features: list[dict[str, Any]] = []
    for zone in zones:
        zone_id = str(zone["zone_id"])
        properties: dict[str, Any] = {
            "zone_id": zone_id,
            "population": round(float(zone["population"]), 4),
            "classification": "C",
        }
        for kind in SHELTER_KINDS:
            before = zone_access[zone_id][f"{kind}_baseline_minutes"]
            after = zone_access[zone_id][f"{kind}_disrupted_minutes"]
            properties[f"{kind}_baseline_minutes"] = None if not math.isfinite(before) else round(before, 2)
            properties[f"{kind}_disrupted_minutes"] = None if not math.isfinite(after) else round(after, 2)
            properties[f"{kind}_delta_minutes"] = (
                None if not (math.isfinite(before) and math.isfinite(after)) else round(after - before, 2)
            )
        zone_features.append(
            {
                "type": "Feature",
                "id": zone_id,
                "properties": properties,
                "geometry": {"type": "Point", "coordinates": [zone["lon"], zone["lat"]]},
            }
        )
    (output / "shelter_population_access.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": zone_features}, ensure_ascii=False),
        encoding="utf-8",
    )
    (output / "shelter_accessibility.json").write_text(
        json.dumps(
            {
                "stage": "A1.9",
                "reference_time": "08:00",
                "scenario": summary["scenario"],
                "registry": summary["shelter_registry"],
                "by_kind": access_by_kind,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "stage": "A1.9",
                "matching": matching_stats["by_kind"],
                "accessibility": {
                    kind: {
                        "usable_destinations": access_by_kind[kind]["usable_destinations"],
                        "baseline_30min": access_by_kind[kind]["baseline"]["reachable_30min"],
                        "disrupted_30min": access_by_kind[kind]["disrupted"]["reachable_30min"],
                        "gt1min_affected": access_by_kind[kind]["impact"]["population_with_gt_1min_increase"],
                        "mean_change": access_by_kind[kind]["impact"]["mean_minutes_change"],
                    }
                    for kind in SHELTER_KINDS
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "a1_9")
    args = parser.parse_args()
    summary = build(args.output)
    return 0 if all(summary["shelter_accessibility"][kind]["usable_destinations"] > 0 for kind in SHELTER_KINDS) else 2


if __name__ == "__main__":
    raise SystemExit(main())
