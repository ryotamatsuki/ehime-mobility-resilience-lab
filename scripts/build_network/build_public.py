"""Build compact public artifacts from locally acquired, licensed inputs."""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from common.provenance import make_provenance, sha256_file
from road.network import RoadNetwork


OSM_PATH = ROOT / "data" / "raw" / "osm" / "ehime_major_roads.json"
POP_PATH = (
    ROOT
    / "data"
    / "raw"
    / "mlit"
    / "population"
    / "extracted"
    / "500m_mesh_2024_38_GEOJSON"
    / "500m_mesh_2024_38.geojson"
)
ROAD_CENSUS_PATH = ROOT / "data" / "raw" / "mlit" / "zkntrf38.csv"
OUT = ROOT / "web" / "data"


def _centroid(geometry: dict[str, Any]) -> tuple[float, float]:
    coordinates = geometry.get("coordinates", [])
    if geometry.get("type") == "Polygon" and coordinates:
        points = coordinates[0]
    else:
        points = coordinates
    if not points:
        return 0.0, 0.0
    lon = sum(float(point[0]) for point in points) / len(points)
    lat = sum(float(point[1]) for point in points) / len(points)
    return lon, lat


def build_population() -> dict[str, Any]:
    data = json.loads(POP_PATH.read_text(encoding="utf-8"))
    aggregate: dict[tuple[float, float], dict[str, float]] = defaultdict(
        lambda: {"population_2020": 0.0, "population_2025": 0.0, "elderly_65plus_2025": 0.0, "mesh_count": 0}
    )
    for feature in data.get("features", []):
        properties = feature.get("properties") or {}
        lon, lat = _centroid(feature.get("geometry") or {})
        grid_lon = math.floor(lon * 10) / 10
        grid_lat = math.floor(lat * 10) / 10
        bucket = aggregate[(grid_lon, grid_lat)]
        for target, source in (
            ("population_2020", "PTN_2020"),
            ("population_2025", "PTN_2025"),
            ("elderly_65plus_2025", "PTC_2025"),
        ):
            value = properties.get(source)
            if value is not None:
                bucket[target] += float(value)
        bucket["mesh_count"] += 1
    features = []
    for (lon, lat), values in sorted(aggregate.items()):
        if values["population_2025"] <= 0 and values["population_2020"] <= 0:
            continue
        coordinates = [
            [lon, lat],
            [lon + 0.1, lat],
            [lon + 0.1, lat + 0.1],
            [lon, lat + 0.1],
            [lon, lat],
        ]
        features.append(
            {
                "type": "Feature",
                "id": f"grid-{lon:.1f}-{lat:.1f}",
                "properties": {
                    "zone_id": f"grid-{lon:.1f}-{lat:.1f}",
                    "population_2020": round(values["population_2020"], 4),
                    "population_2025": round(values["population_2025"], 4),
                    "elderly_65plus_2025": round(values["elderly_65plus_2025"], 4),
                    "mesh_count": int(values["mesh_count"]),
                    "classification": "B",
                    "source_resolution": "500m mesh aggregated for public bundle",
                },
                "geometry": {"type": "Polygon", "coordinates": [coordinates]},
            }
        )
    return {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "source": "MLIT R6 future population mesh 500m",
            "license": "CC-BY-4.0",
            "classification": "B",
            "note": "Public bundle aggregates the acquired 500m mesh into 0.1 degree cells.",
        },
    }


def build_road_census() -> dict[str, Any]:
    if not ROAD_CENSUS_PATH.exists():
        return {"status": "unavailable", "classification": "A", "records": []}
    with ROAD_CENSUS_PATH.open(encoding="cp932", errors="replace", newline="") as handle:
        rows = list(csv.DictReader(handle))
    records: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("車種区分") != "1":
            continue
        section = str(row.get("交通量調査単位区間番号", ""))
        if not section:
            continue
        record = records.setdefault(
            section,
            {
                "section_id": section,
                "road_type": row.get("道路種別"),
                "route_number": row.get("路線番号"),
                "observed_flag": row.get("令和３年度調査交通量観測・非観測の別"),
                "directions": {},
            },
        )
        direction = str(row.get("上り・下りの別", ""))
        raw_volume = str(row.get("２４時間自動車類交通量（台）") or "").strip()
        record["directions"][direction] = float(raw_volume) if raw_volume else 0.0
    compact = []
    for _section, record in sorted(records.items()):
        record["observed_24h_total"] = round(sum(record["directions"].values()), 2)
        del record["directions"]
        record["classification"] = "A"
        compact.append(record)
    return {
        "status": "available",
        "classification": "A",
        "source": "MLIT R3 road census zkntrf38.csv",
        "checksum": sha256_file(ROAD_CENSUS_PATH),
        "records": compact,
    }


def nearest_node(network: RoadNetwork, lon: float, lat: float) -> str:
    best = None
    best_distance = float("inf")
    for node in network.nodes:
        _, node_lat, node_lon = node.split(":")
        distance = (float(node_lat) - lat) ** 2 + (float(node_lon) - lon) ** 2
        if distance < best_distance:
            best = node
            best_distance = distance
    if best is None:
        raise ValueError("network has no nodes")
    return best


def population_zones(population: dict[str, Any]) -> list[dict[str, float]]:
    result = []
    for feature in population["features"]:
        properties = feature["properties"]
        coordinates = feature["geometry"]["coordinates"][0]
        lon = sum(point[0] for point in coordinates[:-1]) / (len(coordinates) - 1)
        lat = sum(point[1] for point in coordinates[:-1]) / (len(coordinates) - 1)
        result.append(
            {
                "zone_id": properties["zone_id"],
                "population": properties["population_2025"],
                "lon": lon,
                "lat": lat,
            }
        )
    return result


def access_metrics(network: RoadNetwork, zones: list[dict[str, float]], disabled: set[str]) -> dict[str, float]:
    total_population = sum(zone["population"] for zone in zones)
    weighted_center = (
        sum(zone["lon"] * zone["population"] for zone in zones) / total_population,
        sum(zone["lat"] * zone["population"] for zone in zones) / total_population,
    )
    anchor = nearest_node(network, *weighted_center)
    baseline: dict[str, float] = {}
    after: dict[str, float] = {}
    for zone in zones:
        source = nearest_node(network, zone["lon"], zone["lat"])
        baseline[zone["zone_id"]] = network.dijkstra(source)[0].get(anchor, float("inf"))
        after[zone["zone_id"]] = network.dijkstra(source, disabled=disabled)[0].get(anchor, float("inf"))
    increased = [
        zone
        for zone in zones
        if after[zone["zone_id"]] > baseline[zone["zone_id"]] + 1e-9
        or (math.isinf(after[zone["zone_id"]]) and not math.isinf(baseline[zone["zone_id"]]))
    ]
    deltas = [
        after[zone["zone_id"]] - baseline[zone["zone_id"]]
        for zone in zones
        if math.isfinite(baseline[zone["zone_id"]]) and math.isfinite(after[zone["zone_id"]])
    ]
    reachable_60_before = sum(
        zone["population"] for zone in zones if baseline[zone["zone_id"]] <= 60
    )
    reachable_60_after = sum(
        zone["population"] for zone in zones if after[zone["zone_id"]] <= 60
    )
    return {
        "anchor_node": anchor,
        "population_total_2025": round(total_population, 2),
        "zones_with_increased_travel_time": len(increased),
        "population_with_increased_travel_time": round(sum(zone["population"] for zone in increased), 2),
        "average_travel_time_delta_minutes": round(sum(deltas) / len(deltas), 3) if deltas else 0.0,
        "reachable_population_60min_before": round(reachable_60_before, 2),
        "reachable_population_60min_after": round(reachable_60_after, 2),
        "accessibility_loss_60min": round(reachable_60_before - reachable_60_after, 2),
    }


def choose_critical_way(network: RoadNetwork) -> tuple[str, set[str], dict[str, Any]]:
    candidates = []
    for edge in network.sorted_edges():
        ref = str(edge.attributes.get("ref", ""))
        if ref in {"56", "国道56号"}:
            candidates.append(edge)
    if not candidates:
        candidates = list(network.sorted_edges())
    selected = max(candidates, key=lambda edge: (edge.length_km, edge.edge_id))
    way_id = str(selected.attributes.get("osm_way_id"))
    disabled = {
        edge.edge_id
        for edge in network.edges.values()
        if str(edge.attributes.get("osm_way_id")) == way_id
    }
    return (
        way_id,
        disabled,
        {
            "link_id": f"osm-way-{way_id}",
            "osm_way_id": way_id,
            "name": selected.attributes.get("name", ""),
            "ref": selected.attributes.get("ref", ""),
            "edge_count": len(disabled),
            "classification": "D",
        },
    )


def build() -> None:
    if not OSM_PATH.exists() or not POP_PATH.exists():
        raise FileNotFoundError("acquired OSM and population inputs are required; see DATA_INVENTORY.md")
    OUT.mkdir(parents=True, exist_ok=True)
    network = RoadNetwork.from_osm_json(OSM_PATH)
    population = build_population()
    zones = population_zones(population)
    way_id, disabled, link = choose_critical_way(network)
    before = access_metrics(network, zones, set())
    after = access_metrics(network, zones, disabled)
    network_geojson = network.to_geojson(OSM_PATH)
    network_geojson["properties"]["generated_from_checksum"] = sha256_file(OSM_PATH)
    network_geojson["properties"]["generated_at"] = "2026-08-22"
    (OUT / "network.geojson").write_text(
        json.dumps(network_geojson, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (OUT / "population_zones.geojson").write_text(
        json.dumps(population, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    census = build_road_census()
    (OUT / "road_census_summary.json").write_text(
        json.dumps(census, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    provenance = make_provenance(
        "ehime-road-accessibility-2025",
        "C",
        "road-access-v0.1.0",
        [
            {"dataset_id": "osm_ehime_major_roads", "checksum": sha256_file(OSM_PATH), "classification": "B"},
            {"dataset_id": "mlit_future_population_mesh500_r6_ehime", "classification": "B"},
        ],
        {
            "population_year": 2025,
            "anchor": "population-weighted network node",
            "road_defaults": "highway and lanes based",
            "disabled_link": link["link_id"],
        },
        scenario_id="road56-stress-test",
        limitations=[
            "Major-road snapshot, not a complete all-road network.",
            "Population zones are aggregated from 500m mesh for public display.",
            "The result is a network stress test, not damage prediction.",
        ],
        repository=ROOT,
    )
    result = {
        "status": "computed",
        "scenario_id": "road56-stress-test",
        "title": "国道56号区間停止チェック（Stress Test）",
        "classification": "D",
        "link": link,
        "baseline": before,
        "after": after,
        "provenance": provenance,
        "transit": {
            "status": "external_input_required",
            "message": "伊予鉄バス等のGTFSは提供条件・認証確認後に投入する。",
            "classification": "A",
        },
        "traffic": {
            "status": "not_computed",
            "message": "県内詳細自動車ODの公式入力が未取得のため、モデル配分値を公開していない。",
            "classification": "C",
        },
        "freight": {
            "status": "not_computed",
            "message": "広域物流統計は台帳化済みだが、公開用の県内細粒度貨物施設入力が未確定。",
            "classification": "C",
        },
        "relief": {
            "status": "not_computed",
            "message": "位置とライセンスを確認した救援拠点入力が未確定。",
            "classification": "C",
        },
    }
    (OUT / "metrics.json").write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    manifest = {
        "manifest_version": "1.0.0",
        "generated_at": "2026-08-22",
        "git_sha": None,
        "artifacts": [
            {"path": "network.geojson", "classification": "B", "status": "available"},
            {"path": "population_zones.geojson", "classification": "B", "status": "available"},
            {"path": "road_census_summary.json", "classification": "A", "status": census["status"]},
            {"path": "metrics.json", "classification": "C", "status": "available"},
        ],
        "blocked": ["Phase B hazard GIS", "unlicensed or unauthenticated GTFS raw feed"],
        "public_limitations": [
            "This is a stress test, not a real damage forecast.",
            "Traffic assignment, freight and relief modules show not_computed until required inputs are licensed and available.",
        ],
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"network_edges": len(network.edges), "population_zones": len(zones), "critical_way": way_id}, ensure_ascii=False))


if __name__ == "__main__":
    build()