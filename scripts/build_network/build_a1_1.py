"""Build the A1.1 real-data Ozu accessibility slice."""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
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
    min_walk_minutes_to_facility,
    stop_walk_times,
    summarize_population_access,
    walking_graph_from_overpass,
)
from common.provenance import make_provenance
from gtfs.reader import GTFSFeed

GTFS_URL = "https://www.city.ozu.ehime.jp/uploaded/attachment/47696.zip"
GTFS_LANDING = "https://www.city.ozu.ehime.jp/site/opendata/44871.html"
POP_URL = "https://gtfs-gis.jp/data/100m_pop2020/38/100m_mesh_pop2020_38207.zip"
POP_LANDING = "https://gtfs-gis.jp/teikyo/"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
ANALYSIS_DATE = date(2026, 8, 21)
DEPARTURE_SECONDS = 8 * 3600
PADDING_DEGREES = 0.02


def fetch(url: str, *, data: bytes | None = None, timeout: int = 60) -> bytes:
    request = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "ehime-mobility-resilience-lab/0.1"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def load_feed(payload: bytes) -> GTFSFeed:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        files: dict[str, list[dict[str, str]]] = {}
        for name in archive.namelist():
            if not name.lower().endswith(".txt"):
                continue
            text = archive.read(name).decode("utf-8-sig")
            files[Path(name).name] = list(csv.DictReader(io.StringIO(text)))
    return GTFSFeed(files)


def first_csv_rows(payload: bytes) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        candidates = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not candidates:
            raise ValueError("population archive contains no CSV")
        raw = archive.read(candidates[0])
    for encoding in ("utf-8-sig", "cp932", "shift_jis"):
        try:
            return list(csv.DictReader(io.StringIO(raw.decode(encoding))))
        except UnicodeDecodeError:
            continue
    raise ValueError("population CSV cannot be decoded")


def mesh100m_center(meshcode: str) -> tuple[float, float]:
    """Return the approximate centre of a 10-digit Japanese 100 m mesh."""
    code = str(meshcode).strip()
    if len(code) < 10 or not code[:10].isdigit():
        raise ValueError(f"unsupported mesh code: {meshcode}")
    lat = int(code[:2]) * 2 / 3
    lon = int(code[2:4]) + 100
    lat += int(code[4]) * 5 / 60
    lon += int(code[5]) * 7.5 / 60
    lat += int(code[6]) * 30 / 3600
    lon += int(code[7]) * 45 / 3600
    quadrant = int(code[8])
    if quadrant in (3, 4):
        lat += 15 / 3600
    if quadrant in (2, 4):
        lon += 22.5 / 3600
    quadrant2 = int(code[9])
    if quadrant2 in (3, 4):
        lat += 7.5 / 3600
    if quadrant2 in (2, 4):
        lon += 11.25 / 3600
    lat += 3.75 / 3600
    lon += 5.625 / 3600
    return lat, lon


def gtfs_bbox(feed: GTFSFeed) -> tuple[float, float, float, float]:
    lats = [float(row["stop_lat"]) for row in feed.files["stops.txt"]]
    lons = [float(row["stop_lon"]) for row in feed.files["stops.txt"]]
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
  node["amenity"="hospital"]({box});
  way["amenity"="hospital"]({box});
  relation["amenity"="hospital"]({box});
);
out body geom;
""".strip()
    payload = fetch(
        OVERPASS_URL,
        data=urllib.parse.urlencode({"data": query}).encode(),
        timeout=120,
    )
    return json.loads(payload.decode("utf-8"))


def population_zones(
    rows: list[dict[str, str]],
    bbox: tuple[float, float, float, float],
) -> list[dict[str, Any]]:
    south, west, north, east = bbox
    zones: list[dict[str, Any]] = []
    for row in rows:
        lat, lon = mesh100m_center(row["Meshcode"])
        population = float(row.get("PopT") or 0.0)
        if population <= 0 or not (south <= lat <= north and west <= lon <= east):
            continue
        # The source already contains age-group estimates at 100 m resolution.
        # Preserve them directly; A1.12 uses these B-classification fields rather
        # than fabricating a new spatial downscale from current regional totals.
        p65 = min(population, max(0.0, float(row.get("Pop65over") or 0.0)))
        p75 = min(p65, max(0.0, float(row.get("Pop75over") or 0.0)))
        p85 = min(p75, max(0.0, float(row.get("Pop85over") or 0.0)))
        zones.append(
            {
                "zone_id": row["Meshcode"],
                "population": population,
                "population_65plus": p65,
                "population_75plus": p75,
                "population_85plus": p85,
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
        item = dict(point)
        item["snap_km"] = round(snap_km, 4)
        mapping[str(item["id"])] = node
        accepted.append(item)
    return mapping, accepted


def zones_to_nodes(
    zones: list[dict[str, Any]],
    index: CoordinateIndex,
    *,
    max_snap_km: float = 1.0,
) -> list[dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
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

    feed = load_feed(fetch(GTFS_URL))
    bbox = gtfs_bbox(feed)
    population_rows = first_csv_rows(fetch(POP_URL))
    osm = fetch_osm(bbox)
    graph, node_coordinates = walking_graph_from_overpass(osm)
    graph_errors = graph.validate()
    if graph_errors:
        raise ValueError("walking graph invalid: " + "; ".join(graph_errors[:20]))
    index = CoordinateIndex(node_coordinates)

    facilities_raw = extract_facilities(osm, allowed={"hospital"})
    facility_nodes, facilities = snap_points(
        [dict(item, id=item["id"]) for item in facilities_raw], index, max_snap_km=0.5
    )
    if not facility_nodes:
        raise ValueError("no hospital destination snapped to walking network")

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
    zones = zones_to_nodes(population_zones(population_rows, bbox), index)
    if not zones:
        raise ValueError("no population zones in analysis envelope")

    facility_walk = min_walk_minutes_to_facility(graph, facility_nodes.values())
    stop_walk = stop_walk_times(graph, stop_nodes)
    connections = sorted(
        feed.connections(ANALYSIS_DATE),
        key=lambda item: (item["departure_seconds"], item["arrival_seconds"]),
    )
    trip_routes = {
        row["trip_id"]: row["route_id"]
        for row in feed.files["trips.txt"]
    }
    route_names = {
        row["route_id"]: row.get("route_long_name") or row.get("route_short_name") or row["route_id"]
        for row in feed.files["routes.txt"]
    }
    right_loop_routes = {
        route_id for route_id, name in route_names.items() if "右回り" in name
    }
    if not right_loop_routes:
        raise ValueError("clockwise loop route not found")

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
        disabled_routes=right_loop_routes,
    )

    provenance = make_provenance(
        "a1-1-ozu-accessibility",
        "C",
        "minimal-multimodal-v0.1.1",
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
            "walking_network": "OSM highway graph",
            "transit_algorithm": "minimal connection scan",
            "stop_to_stop_walking_transfers": False,
        },
        scenario_id="ozu-clockwise-loop-unavailable",
        limitations=[
            "Hospital destinations are OpenStreetMap amenity=hospital features inside the GTFS stop envelope and are not an official hospital registry.",
            "Stop-to-stop walking transfers are not modelled in A1.1.",
            "GTFS has no shapes.txt; route geometry is a stop-order polyline and not road-exact.",
            "Population is a census-derived simplified 100 m allocation and is classification B.",
            "The clockwise-loop outage is a D stress-test assumption, not a disaster damage forecast.",
        ],
        repository=ROOT,
    )

    summary = {
        "stage": "A1.1",
        "status": "computed",
        "title": "大洲市 ぐるりんおおず Minimal Accessibility",
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
        },
        "population": {
            "source_rows": len(population_rows),
            "zones_in_envelope": len(zones),
            "population_in_envelope": round(sum(float(zone["population"]) for zone in zones), 4),
        },
        "scenario": {
            "id": "ozu-clockwise-loop-unavailable",
            "disabled_route_ids": sorted(right_loop_routes),
            "disabled_route_names": [route_names[route_id] for route_id in sorted(right_loop_routes)],
        },
        "baseline": baseline,
        "disrupted": disrupted,
        "provenance": provenance,
    }

    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "stops.geojson").write_text(json.dumps(geojson_points(stops, ["stop_id", "name", "snap_km"]), ensure_ascii=False), encoding="utf-8")
    (output / "facilities.geojson").write_text(json.dumps(geojson_points(facilities, ["name", "amenity", "snap_km"]), ensure_ascii=False), encoding="utf-8")
    route_geojson = feed.route_geojson()
    for feature in route_geojson["features"]:
        feature["properties"]["route_name"] = route_names.get(feature["properties"]["route_id"])
    (output / "routes.geojson").write_text(json.dumps(route_geojson, ensure_ascii=False), encoding="utf-8")

    zone_features: list[dict[str, Any]] = []
    for zone in zones:
        zone_id = str(zone["zone_id"])
        before = baseline_minutes[zone_id]
        after = disrupted_minutes[zone_id]
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
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "a1_1")
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
