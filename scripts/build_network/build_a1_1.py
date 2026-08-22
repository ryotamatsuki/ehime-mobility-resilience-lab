"""Build A1.1 real-data minimal multimodal accessibility outputs.

Inputs are downloaded at runtime and are not persisted as raw repository data:
- Ozu City Gururin Ozu GTFS (CC BY 4.0)
- 2020 100 m simplified population mesh for Ozu City (CC BY)
- OpenStreetMap / Overpass road and essential-facility data (ODbL)

The output is a reproducible model result (classification C) comparing a normal
weekday morning with a user-assumed disruption of all clockwise Gururin routes
(classification D). This is a stress test, not a disaster prediction.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from accessibility.multimodal import (
    CoordinateIndex,
    earliest_arrival_minutes,
    extract_facilities,
    mesh100m_center,
    min_walk_minutes_to_facility,
    stop_walk_times,
    summarize_population_access,
    walking_graph_from_overpass,
)
from common.provenance import make_provenance
from transit.gtfs import GTFSFeed

GTFS_URL = "https://www.city.ozu.ehime.jp/uploaded/attachment/47696.zip"
GTFS_LANDING = "https://www.city.ozu.ehime.jp/site/opendata/44871.html"
POP_URL = "https://gtfs-gis.jp/data/100m_pop2020/38/100m_mesh_pop2020_38207.zip"
POP_LANDING = "https://gtfs-gis.jp/regional_data.html"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
ANALYSIS_DATE = date(2026, 8, 21)
DEPARTURE_SECONDS = 8 * 3600
PADDING_DEGREES = 0.02


def fetch(url: str, *, data: bytes | None = None, timeout: int = 120) -> bytes:
    request = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "EhimeMobilityResilienceLab/0.1 (+GitHub Actions)"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise RuntimeError("unsupported source text encoding")


def first_csv_rows(payload: bytes) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not names:
            raise ValueError("population archive has no CSV")
        return list(csv.DictReader(io.StringIO(decode(archive.read(sorted(names)[0])))))


def gtfs_bbox(feed: GTFSFeed) -> tuple[float, float, float, float]:
    stops = feed.files["stops.txt"]
    lats = [float(row["stop_lat"]) for row in stops]
    lons = [float(row["stop_lon"]) for row in stops]
    return (
        min(lats) - PADDING_DEGREES,
        min(lons) - PADDING_DEGREES,
        max(lats) + PADDING_DEGREES,
        max(lons) + PADDING_DEGREES,
    )


def fetch_osm(bbox: tuple[float, float, float, float]) -> dict[str, Any]:
    south, west, north, east = bbox
    box = f"{south:.6f},{west:.6f},{north:.6f},{east:.6f}"
    query = f"""
[out:json][timeout:90];
(
  way["highway"]({box});
  node["amenity"~"hospital|clinic|townhall"]({box});
  way["amenity"~"hospital|clinic|townhall"]({box});
);
out body geom;
""".strip()
    payload = fetch(
        OVERPASS_URL,
        data=urllib.parse.urlencode({"data": query}).encode(),
        timeout=120,
    )
    return json.loads(payload.decode("utf-8"))


def load_feed(payload: bytes) -> GTFSFeed:
    with tempfile.NamedTemporaryFile(suffix=".zip") as handle:
        handle.write(payload)
        handle.flush()
        feed = GTFSFeed.from_zip(handle.name, feed_id="ozu-gururin-20260401")
    errors = feed.validate()
    if errors:
        raise ValueError("GTFS validation failed: " + "; ".join(errors[:20]))
    return feed


def population_zones(
    rows: list[dict[str, str]],
    bbox: tuple[float, float, float, float],
) -> list[dict[str, Any]]:
    south, west, north, east = bbox
    zones = []
    for row in rows:
        lat, lon = mesh100m_center(row["Meshcode"])
        population = float(row.get("PopT") or 0.0)
        if population <= 0 or not (south <= lat <= north and west <= lon <= east):
            continue
        zones.append(
            {
                "zone_id": row["Meshcode"],
                "population": population,
                "population_65plus": float(row.get("Pop65over") or 0.0),
                "lat": lat,
                "lon": lon,
            }
        )
    return zones


def snap_points(
    points: list[dict[str, Any]],
    index: CoordinateIndex,
    *,
    max_snap_km: float,
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    mapping: dict[str, str] = {}
    accepted: list[dict[str, Any]] = []
    for point in points:
        node, snap_km = index.nearest(float(point["lat"]), float(point["lon"]))
        if snap_km > max_snap_km:
            continue
        point = dict(point)
        point["snap_km"] = round(snap_km, 4)
        mapping[str(point["id"])] = node
        accepted.append(point)
    return mapping, accepted


def zones_to_nodes(
    zones: list[dict[str, Any]],
    index: CoordinateIndex,
    *,
    max_snap_km: float = 1.0,
) -> list[dict[str, Any]]:
    accepted = []
    for zone in zones:
        node, snap_km = index.nearest(float(zone["lat"]), float(zone["lon"]))
        if snap_km > max_snap_km:
            continue
        item = dict(zone)
        item["node"] = node
        item["snap_km"] = round(snap_km, 4)
        accepted.append(item)
    return accepted


def evaluate(
    *,
    zones: list[dict[str, Any]],
    connections: list[dict[str, Any]],
    trip_routes: dict[str, str],
    stop_walk: dict[str, dict[str, float]],
    facility_walk_by_node: dict[str, float],
    stop_nodes: dict[str, str],
    disabled_routes: set[str],
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
        )
    return values, summarize_population_access(zones, values)


def geojson_points(items: list[dict[str, Any]], properties: list[str]) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": str(item.get("id", item.get("zone_id", ""))),
                "properties": {key: item.get(key) for key in properties},
                "geometry": {"type": "Point", "coordinates": [item["lon"], item["lat"]]},
            }
            for item in items
        ],
    }


def build(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    gtfs_payload = fetch(GTFS_URL)
    feed = load_feed(gtfs_payload)
    bbox = gtfs_bbox(feed)
    population_payload = fetch(POP_URL)
    population_rows = first_csv_rows(population_payload)
    osm = fetch_osm(bbox)

    graph, node_coordinates = walking_graph_from_overpass(osm)
    graph_errors = graph.validate()
    if graph_errors:
        raise ValueError("walking graph invalid: " + "; ".join(graph_errors[:20]))
    index = CoordinateIndex(node_coordinates)

    facilities = extract_facilities(osm)
    facility_points = [dict(item, id=item["id"]) for item in facilities]
    facility_nodes, facilities = snap_points(facility_points, index, max_snap_km=0.5)
    if not facility_nodes:
        raise ValueError("no essential facilities could be snapped to the walking network")

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

    raw_zones = population_zones(population_rows, bbox)
    zones = zones_to_nodes(raw_zones, index)
    if not zones:
        raise ValueError("no population zones available in A1.1 service envelope")

    facility_walk = min_walk_minutes_to_facility(graph, facility_nodes.values())
    stop_walk = stop_walk_times(graph, stop_nodes)
    connections = feed.connections(ANALYSIS_DATE)
    if not connections:
        raise ValueError(f"GTFS has no connections on {ANALYSIS_DATE}")
    trip_routes = {row["trip_id"]: row["route_id"] for row in feed.files["trips.txt"]}
    route_names = {row["route_id"]: row.get("route_long_name", row["route_id"]) for row in feed.files["routes.txt"]}
    disabled_routes = {route_id for route_id, name in route_names.items() if "右回り" in name}
    if not disabled_routes:
        raise ValueError("clockwise stress-test routes were not found")

    baseline_minutes, baseline = evaluate(
        zones=zones,
        connections=connections,
        trip_routes=trip_routes,
        stop_walk=stop_walk,
        facility_walk_by_node=facility_walk,
        stop_nodes=stop_nodes,
        disabled_routes=set(),
    )
    disrupted_minutes, disrupted = evaluate(
        zones=zones,
        connections=connections,
        trip_routes=trip_routes,
        stop_walk=stop_walk,
        facility_walk_by_node=facility_walk,
        stop_nodes=stop_nodes,
        disabled_routes=disabled_routes,
    )

    affected_population = sum(
        float(zone["population"])
        for zone in zones
        if disrupted_minutes[str(zone["zone_id"])] > baseline_minutes[str(zone["zone_id"])] + 1.0
    )
    loss_60 = baseline["reachable_60min"] - disrupted["reachable_60min"]
    provenance = make_provenance(
        "a1-1-ozu-minimal-accessibility",
        "C",
        "minimal-multimodal-v0.1.0",
        [
            {"dataset_id": "ozu_gururin_gtfs_20260401", "source": GTFS_LANDING, "classification": "A", "license": "CC BY 4.0"},
            {"dataset_id": "ozu_population_100m_2020", "source": POP_LANDING, "classification": "B", "license": "CC BY"},
            {"dataset_id": "osm_ozu_gtfs_envelope", "source": "https://www.openstreetmap.org/copyright", "classification": "B", "license": "ODbL 1.0"},
        ],
        {
            "analysis_date": ANALYSIS_DATE.isoformat(),
            "departure_time": "08:00:00",
            "walking_speed_kmh": 4.8,
            "max_access_walk_minutes": 20,
            "analysis_extent": "GTFS stop bbox + 0.02 degrees",
            "facility_types": ["hospital", "clinic", "townhall"],
            "disabled_routes": sorted(disabled_routes),
        },
        scenario_id="ozu-clockwise-loop-unavailable",
        limitations=[
            "A1.1 covers the Gururin Ozu service envelope, not all Ehime Prefecture.",
            "Walking uses an OSM-derived graph; stop-to-stop walking transfers are not yet modelled.",
            "Population is a census-derived simplified 100 m allocation and is classification B.",
            "The clockwise-route outage is a user-defined stress-test assumption (D), not a damage forecast.",
            "GTFS has no shapes.txt; public route geometry therefore uses stop-order polylines.",
        ],
        repository=ROOT,
    )

    summary = {
        "stage": "A1.1",
        "status": "computed",
        "title": "大洲市 ぐるりんおおず 最小Accessibility Stress Test",
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
            "essential_facilities": len(facilities),
        },
        "population": {
            "source_rows": len(population_rows),
            "zones_in_envelope": len(zones),
            "population_in_envelope": round(sum(float(zone["population"]) for zone in zones), 4),
        },
        "scenario": {
            "id": "ozu-clockwise-loop-unavailable",
            "disabled_route_ids": sorted(disabled_routes),
            "disabled_route_names": [route_names[route_id] for route_id in sorted(disabled_routes)],
        },
        "baseline": baseline,
        "disrupted": disrupted,
        "impact": {
            "accessibility_loss_60min_population": round(loss_60, 4),
            "population_with_gt_1min_increase": round(affected_population, 4),
            "mean_minutes_change": round(
                disrupted["population_weighted_mean_minutes"] - baseline["population_weighted_mean_minutes"],
                3,
            ),
        },
        "provenance": provenance,
    }

    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "stops.geojson").write_text(
        json.dumps(geojson_points(stops, ["stop_id", "name", "snap_km"]), ensure_ascii=False),
        encoding="utf-8",
    )
    (output / "facilities.geojson").write_text(
        json.dumps(geojson_points(facilities, ["name", "amenity", "snap_km"]), ensure_ascii=False),
        encoding="utf-8",
    )
    route_geojson = feed.route_geojson()
    for feature in route_geojson["features"]:
        feature["properties"]["route_name"] = route_names.get(feature["properties"]["route_id"])
    (output / "routes.geojson").write_text(json.dumps(route_geojson, ensure_ascii=False), encoding="utf-8")
    zone_features = []
    for zone in zones:
        zone_id = str(zone["zone_id"])
        base = baseline_minutes[zone_id]
        after = disrupted_minutes[zone_id]
        zone_features.append(
            {
                "type": "Feature",
                "id": zone_id,
                "properties": {
                    "zone_id": zone_id,
                    "population": round(float(zone["population"]), 4),
                    "baseline_minutes": None if not math.isfinite(base) else round(base, 2),
                    "disrupted_minutes": None if not math.isfinite(after) else round(after, 2),
                    "delta_minutes": None if not (math.isfinite(base) and math.isfinite(after)) else round(after - base, 2),
                    "classification": "C",
                },
                "geometry": {"type": "Point", "coordinates": [zone["lon"], zone["lat"]]},
            }
        )
    (output / "population_access.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": zone_features}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "a1_1")
    args = parser.parse_args()
    summary = build(args.output)
    if summary["gtfs"]["snapped_stops"] < 1 or summary["population"]["zones_in_envelope"] < 1:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
