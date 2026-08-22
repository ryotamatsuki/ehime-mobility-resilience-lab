"""Minimal, deterministic walk + scheduled-transit accessibility helpers for A1.1.

The module deliberately stays dependency-free. It is not a full journey planner:
walking is routed on an OSM-derived pedestrian graph, scheduled bus movement is
handled with a connection-scan pass, and stop-to-stop walking transfers are not
yet included. Those limitations are surfaced in provenance instead of hidden.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from common.graph import DirectedGraph, Edge

WALK_SPEED_KMH = 4.8
NON_WALKABLE_HIGHWAYS = {"motorway", "motorway_link", "construction", "proposed"}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = p2 - p1
    dlambda = math.radians(lon2 - lon1)
    value = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return r * 2 * math.asin(math.sqrt(value))


def mesh100m_center(meshcode: str) -> tuple[float, float]:
    """Return the WGS84-like centre of a Japanese 10-digit 100 m mesh cell.

    10-digit mesh codes subdivide the standard 1 km third mesh into ten parts
    north-south and east-west. Returned coordinates are suitable for the public
    census-derived mesh used in A1.1; no claim of survey-grade precision is made.
    """

    code = str(meshcode).strip()
    if len(code) != 10 or not code.isdigit():
        raise ValueError(f"expected 10-digit mesh code, got {meshcode!r}")
    lat = int(code[0:2]) * 2.0 / 3.0
    lon = int(code[2:4]) + 100.0
    lat += int(code[4]) / 12.0
    lon += int(code[5]) / 8.0
    lat += int(code[6]) / 120.0
    lon += int(code[7]) / 80.0
    lat_step = 1.0 / 1200.0
    lon_step = 1.0 / 800.0
    lat += int(code[8]) * lat_step + lat_step / 2.0
    lon += int(code[9]) * lon_step + lon_step / 2.0
    return lat, lon


def _node_key(lat: float, lon: float) -> str:
    return f"w:{lat:.7f}:{lon:.7f}"


def walking_graph_from_overpass(data: dict[str, Any]) -> tuple[DirectedGraph, dict[str, tuple[float, float]]]:
    graph = DirectedGraph()
    coordinates: dict[str, tuple[float, float]] = {}
    seen_edges: set[str] = set()
    for element in data.get("elements", []):
        if element.get("type") != "way" or not (element.get("tags") or {}).get("highway"):
            continue
        tags = element.get("tags") or {}
        highway = str(tags.get("highway", ""))
        if highway in NON_WALKABLE_HIGHWAYS or str(tags.get("access", "")).lower() in {"no", "private"}:
            continue
        if str(tags.get("foot", "")).lower() == "no":
            continue
        geometry = element.get("geometry") or []
        for index, (first, second) in enumerate(zip(geometry, geometry[1:])):
            a = (float(first["lat"]), float(first["lon"]))
            b = (float(second["lat"]), float(second["lon"]))
            u = _node_key(*a)
            v = _node_key(*b)
            coordinates[u] = a
            coordinates[v] = b
            length = max(haversine_km(*a, *b), 0.001)
            base = f"walk:{element.get('id')}:{index}"
            for suffix, source, target in (("f", u, v), ("r", v, u)):
                edge_id = f"{base}:{suffix}"
                if edge_id in seen_edges:
                    continue
                seen_edges.add(edge_id)
                graph.add_edge(
                    Edge(
                        edge_id=edge_id,
                        u=source,
                        v=target,
                        length_km=length,
                        free_speed_kmh=WALK_SPEED_KMH,
                        capacity_vph=0.0,
                        mode="walk",
                        attributes={"osm_way_id": element.get("id"), "highway": highway},
                    )
                )
    return graph, coordinates


@dataclass
class CoordinateIndex:
    coordinates: dict[str, tuple[float, float]]
    cell_degrees: float = 0.005

    def __post_init__(self) -> None:
        self._buckets: dict[tuple[int, int], list[str]] = defaultdict(list)
        for node, (lat, lon) in self.coordinates.items():
            self._buckets[self._bucket(lat, lon)].append(node)

    def _bucket(self, lat: float, lon: float) -> tuple[int, int]:
        return math.floor(lat / self.cell_degrees), math.floor(lon / self.cell_degrees)

    def nearest(self, lat: float, lon: float, max_ring: int = 8) -> tuple[str, float]:
        base_i, base_j = self._bucket(lat, lon)
        candidates: list[str] = []
        for ring in range(max_ring + 1):
            for di in range(-ring, ring + 1):
                for dj in range(-ring, ring + 1):
                    if ring and max(abs(di), abs(dj)) != ring:
                        continue
                    candidates.extend(self._buckets.get((base_i + di, base_j + dj), []))
            if candidates:
                break
        if not candidates:
            candidates = list(self.coordinates)
        if not candidates:
            raise ValueError("walking graph has no nodes")
        best = min(
            candidates,
            key=lambda node: haversine_km(lat, lon, self.coordinates[node][0], self.coordinates[node][1]),
        )
        best_lat, best_lon = self.coordinates[best]
        return best, haversine_km(lat, lon, best_lat, best_lon)


def extract_facilities(overpass: dict[str, Any], allowed: set[str] | None = None) -> list[dict[str, Any]]:
    allowed = allowed or {"hospital", "clinic", "townhall"}
    facilities: list[dict[str, Any]] = []
    for element in overpass.get("elements", []):
        tags = element.get("tags") or {}
        amenity = str(tags.get("amenity", ""))
        if amenity not in allowed:
            continue
        if element.get("type") == "node" and "lat" in element and "lon" in element:
            lat, lon = float(element["lat"]), float(element["lon"])
        else:
            geometry = element.get("geometry") or []
            if not geometry:
                continue
            lat = sum(float(point["lat"]) for point in geometry) / len(geometry)
            lon = sum(float(point["lon"]) for point in geometry) / len(geometry)
        facilities.append(
            {
                "id": f"osm:{element.get('type')}:{element.get('id')}",
                "name": tags.get("name") or tags.get("name:ja") or amenity,
                "amenity": amenity,
                "lat": lat,
                "lon": lon,
            }
        )
    return facilities


def min_walk_minutes_to_facility(
    graph: DirectedGraph,
    facility_nodes: Iterable[str],
) -> dict[str, float]:
    minimum = {node: math.inf for node in graph.nodes}
    for facility_node in sorted(set(facility_nodes)):
        distances, _ = graph.dijkstra(facility_node)
        for node, minutes in distances.items():
            if minutes < minimum.get(node, math.inf):
                minimum[node] = minutes
    return minimum


def stop_walk_times(
    graph: DirectedGraph,
    stop_nodes: dict[str, str],
) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for stop_id, node in sorted(stop_nodes.items()):
        result[stop_id] = graph.dijkstra(node)[0]
    return result


def earliest_arrival_minutes(
    *,
    zone_node: str,
    departure_seconds: int,
    connections: list[dict[str, Any]],
    trip_routes: dict[str, str],
    stop_walk: dict[str, dict[str, float]],
    facility_walk_by_node: dict[str, float],
    stop_nodes: dict[str, str],
    disabled_routes: set[str] | None = None,
    max_access_walk_minutes: float = 20.0,
) -> float:
    disabled_routes = disabled_routes or set()
    direct = facility_walk_by_node.get(zone_node, math.inf)
    arrival: dict[str, int] = {}
    for stop_id, node_distances in stop_walk.items():
        walk_minutes = node_distances.get(zone_node, math.inf)
        if walk_minutes <= max_access_walk_minutes:
            arrival[stop_id] = departure_seconds + int(round(walk_minutes * 60.0))
    for connection in sorted(connections, key=lambda item: (item["departure_seconds"], item["arrival_seconds"])):
        trip_id = str(connection["trip_id"])
        if trip_routes.get(trip_id) in disabled_routes:
            continue
        from_stop = str(connection["from_stop"])
        to_stop = str(connection["to_stop"])
        if arrival.get(from_stop, 10**12) <= int(connection["departure_seconds"]):
            candidate = int(connection["arrival_seconds"])
            if candidate < arrival.get(to_stop, 10**12):
                arrival[to_stop] = candidate
    best = direct
    for stop_id, arrival_seconds in arrival.items():
        stop_node = stop_nodes.get(stop_id)
        if stop_node is None:
            continue
        egress = facility_walk_by_node.get(stop_node, math.inf)
        if math.isfinite(egress):
            total = (arrival_seconds - departure_seconds) / 60.0 + egress
            best = min(best, total)
    return best


def summarize_population_access(
    zones: Iterable[dict[str, Any]],
    minutes: dict[str, float],
    thresholds: tuple[int, ...] = (30, 60, 90),
) -> dict[str, float]:
    zone_list = list(zones)
    total = sum(float(zone["population"]) for zone in zone_list)
    result: dict[str, float] = {"population": round(total, 4), "zones": float(len(zone_list))}
    for threshold in thresholds:
        value = sum(
            float(zone["population"])
            for zone in zone_list
            if minutes.get(str(zone["zone_id"]), math.inf) <= threshold
        )
        result[f"reachable_{threshold}min"] = round(value, 4)
        result[f"reachable_{threshold}min_pct"] = round(value / total * 100.0, 3) if total else 0.0
    finite = [
        (float(zone["population"]), minutes.get(str(zone["zone_id"]), math.inf))
        for zone in zone_list
        if math.isfinite(minutes.get(str(zone["zone_id"]), math.inf))
    ]
    weight = sum(pop for pop, _ in finite)
    result["population_weighted_mean_minutes"] = (
        round(sum(pop * value for pop, value in finite) / weight, 3) if weight else math.inf
    )
    return result
