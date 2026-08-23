"""OSM road graph adapter with explicit default assumptions."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from common.graph import DirectedGraph, Edge


DEFAULT_SPEEDS = {
    "motorway": 80.0,
    "trunk": 60.0,
    "primary": 50.0,
    "secondary": 40.0,
    "tertiary": 30.0,
    "residential": 25.0,
}
DEFAULT_LANES = {
    "motorway": 2,
    "trunk": 2,
    "primary": 2,
    "secondary": 1,
    "tertiary": 1,
    "residential": 1,
}


def _node_key(lat: float, lon: float) -> str:
    return f"n:{lat:.7f}:{lon:.7f}"


def _parse_number(value: Any, default: float) -> float:
    if value is None:
        return default
    match = re.search(r"\d+(?:\.\d+)?", str(value))
    if not match:
        return default
    try:
        return float(match.group(0))
    except ValueError:
        return default


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(value))


class RoadNetwork(DirectedGraph):
    @classmethod
    def from_osm_json(cls, path: str | Path) -> "RoadNetwork":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        network = cls()
        for element in data.get("elements", []):
            if element.get("type") != "way":
                continue
            geometry = element.get("geometry") or []
            if len(geometry) < 2:
                continue
            tags = element.get("tags") or {}
            highway = str(tags.get("highway", "road"))
            if highway.endswith("_link"):
                base_highway = highway.removesuffix("_link")
            else:
                base_highway = highway
            speed = _parse_number(
                tags.get("maxspeed"),
                DEFAULT_SPEEDS.get(base_highway, DEFAULT_SPEEDS["secondary"]),
            )
            lanes = max(1.0, _parse_number(tags.get("lanes"), DEFAULT_LANES.get(base_highway, 1)))
            capacity = lanes * 650.0
            oneway = str(tags.get("oneway", "")).lower()
            for index, (first, second) in enumerate(zip(geometry, geometry[1:], strict=False)):
                a = (float(first["lat"]), float(first["lon"]))
                b = (float(second["lat"]), float(second["lon"]))
                length = max(_haversine_km(a, b), 0.001)
                u = _node_key(*a)
                v = _node_key(*b)
                base_id = f"osm:{element.get('id')}:{index}"
                attrs = {
                    "osm_way_id": element.get("id"),
                    "highway": highway,
                    "name": tags.get("name") or tags.get("name:ja") or "",
                    "ref": tags.get("ref") or "",
                    "lanes": lanes,
                    "speed_source": "osm" if tags.get("maxspeed") else "default_by_highway",
                    "capacity_source": "lanes_times_default",
                }
                if oneway == "-1":
                    network.add_edge(
                        Edge(
                            f"{base_id}:rev",
                            v,
                            u,
                            length,
                            speed,
                            capacity,
                            attributes=attrs,
                        )
                    )
                else:
                    network.add_edge(
                        Edge(
                            f"{base_id}:fwd",
                            u,
                            v,
                            length,
                            speed,
                            capacity,
                            attributes=attrs,
                        )
                    )
                    if oneway not in {"yes", "1", "true"}:
                        network.add_edge(
                            Edge(
                                f"{base_id}:rev",
                                v,
                                u,
                                length,
                                speed,
                                capacity,
                                attributes=attrs,
                            )
                        )
        return network

    def to_geojson(self, osm_path: str | Path) -> dict[str, Any]:
        source = json.loads(Path(osm_path).read_text(encoding="utf-8"))
        features: list[dict[str, Any]] = []
        for element in source.get("elements", []):
            geometry = element.get("geometry") or []
            if len(geometry) < 2:
                continue
            tags = element.get("tags") or {}
            coordinates = [[float(point["lon"]), float(point["lat"])] for point in geometry]
            features.append(
                {
                    "type": "Feature",
                    "id": f"osm-way-{element.get('id')}",
                    "properties": {
                        "osm_way_id": element.get("id"),
                        "highway": tags.get("highway"),
                        "name": tags.get("name") or tags.get("name:ja") or "",
                        "ref": tags.get("ref") or "",
                        "source_classification": "B",
                        "selectable": True,
                    },
                    "geometry": {"type": "LineString", "coordinates": coordinates},
                }
            )
        return {
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "source": "OpenStreetMap via Overpass",
                "license": "ODbL-1.0",
                "note": "Major-road snapshot; not a complete all-road network",
            },
        }
