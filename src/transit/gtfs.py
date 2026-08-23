"""GTFS-JP compatible static feed reader without external dependencies."""

from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


REQUIRED_FILES = {"stops.txt", "routes.txt", "trips.txt", "stop_times.txt"}
OPTIONAL_FILES = {"agency.txt", "calendar.txt", "calendar_dates.txt", "shapes.txt", "feed_info.txt"}


def parse_gtfs_time(value: str) -> int:
    parts = str(value).strip().split(":")
    if len(parts) != 3:
        raise ValueError(f"invalid GTFS time: {value}")
    hour, minute, second = (int(part) for part in parts)
    if hour < 0 or minute not in range(60) or second not in range(60):
        raise ValueError(f"invalid GTFS time: {value}")
    return hour * 3600 + minute * 60 + second


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", raw, 0, len(raw), "unsupported GTFS encoding")


def _read_csv(raw: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(_decode(raw))))


@dataclass
class GTFSFeed:
    feed_id: str
    files: dict[str, list[dict[str, str]]]

    @classmethod
    def from_zip(cls, path: str | Path, feed_id: str = "external") -> "GTFSFeed":
        with zipfile.ZipFile(path) as archive:
            names = {name.rsplit("/", 1)[-1] for name in archive.namelist() if not name.endswith("/")}
            missing = sorted(REQUIRED_FILES - names)
            if missing:
                raise ValueError(f"GTFS missing required files: {', '.join(missing)}")
            files = {name: _read_csv(archive.read(name)) for name in sorted(names) if name in REQUIRED_FILES | OPTIONAL_FILES}
        return cls(feed_id=feed_id, files=files)

    @classmethod
    def from_directory(cls, path: str | Path, feed_id: str = "external") -> "GTFSFeed":
        directory = Path(path)
        names = {file.name for file in directory.iterdir() if file.is_file()}
        missing = sorted(REQUIRED_FILES - names)
        if missing:
            raise ValueError(f"GTFS missing required files: {', '.join(missing)}")
        files = {
            name: _read_csv((directory / name).read_bytes())
            for name in sorted(names)
            if name in REQUIRED_FILES | OPTIONAL_FILES
        }
        return cls(feed_id=feed_id, files=files)

    def validate(self) -> list[str]:
        errors: list[str] = []
        required_columns = {
            "stops.txt": {"stop_id", "stop_name", "stop_lat", "stop_lon"},
            "routes.txt": {"route_id", "route_short_name", "route_type"},
            "trips.txt": {"route_id", "service_id", "trip_id"},
            "stop_times.txt": {"trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"},
        }
        for file_name, columns in required_columns.items():
            rows = self.files.get(file_name, [])
            if not rows:
                errors.append(f"{file_name} has no rows")
                continue
            missing = sorted(columns - set(rows[0]))
            errors.extend(f"{file_name} missing column {column}" for column in missing)
        stops = {row.get("stop_id") for row in self.files.get("stops.txt", [])}
        routes = {row.get("route_id") for row in self.files.get("routes.txt", [])}
        trips = {row.get("trip_id"): row for row in self.files.get("trips.txt", [])}
        for row in self.files.get("stops.txt", []):
            try:
                lat = float(row["stop_lat"])
                lon = float(row["stop_lon"])
                if not -90 <= lat <= 90 or not -180 <= lon <= 180:
                    errors.append(f"stop out of range: {row.get('stop_id')}")
            except (KeyError, ValueError):
                errors.append(f"invalid stop coordinate: {row.get('stop_id')}")
        for row in self.files.get("trips.txt", []):
            if row.get("route_id") not in routes:
                errors.append(f"trip references missing route: {row.get('trip_id')}")
        seen_stop_times: set[tuple[str, str]] = set()
        for row in self.files.get("stop_times.txt", []):
            trip_id = row.get("trip_id")
            stop_id = row.get("stop_id")
            if trip_id not in trips:
                errors.append(f"stop_time references missing trip: {trip_id}")
            if stop_id not in stops:
                errors.append(f"stop_time references missing stop: {stop_id}")
            try:
                parse_gtfs_time(row["arrival_time"])
                parse_gtfs_time(row["departure_time"])
                int(row["stop_sequence"])
            except (KeyError, ValueError):
                errors.append(f"invalid stop_time row: {trip_id}/{stop_id}")
            key = (str(trip_id), str(row.get("stop_sequence")))
            if key in seen_stop_times:
                errors.append(f"duplicate stop sequence: {key}")
            seen_stop_times.add(key)
        return sorted(set(errors))

    def service_ids_for_date(self, service_date: date) -> set[str]:
        weekday = service_date.strftime("%A").lower()
        active: set[str] = set()
        for row in self.files.get("calendar.txt", []):
            if row.get("start_date", "") <= service_date.strftime("%Y%m%d") <= row.get("end_date", "") and row.get(weekday) == "1":
                active.add(row["service_id"])
        for row in self.files.get("calendar_dates.txt", []):
            if row.get("date") != service_date.strftime("%Y%m%d"):
                continue
            if row.get("exception_type") == "1":
                active.add(row["service_id"])
            elif row.get("exception_type") == "2":
                active.discard(row["service_id"])
        return active

    def connections(self, service_date: date) -> list[dict[str, Any]]:
        active_services = self.service_ids_for_date(service_date)
        active_trips = {
            row["trip_id"]
            for row in self.files.get("trips.txt", [])
            if row.get("service_id") in active_services
        }
        rows = [
            row
            for row in self.files.get("stop_times.txt", [])
            if row.get("trip_id") in active_trips
        ]
        rows.sort(key=lambda row: (row["trip_id"], int(row["stop_sequence"])))
        by_trip: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            by_trip.setdefault(row["trip_id"], []).append(row)
        result: list[dict[str, Any]] = []
        for trip_id in sorted(by_trip):
            trip_rows = by_trip[trip_id]
            for first, second in zip(trip_rows, trip_rows[1:], strict=False):
                result.append(
                    {
                        "feed_id": self.feed_id,
                        "trip_id": trip_id,
                        "from_stop": first["stop_id"],
                        "to_stop": second["stop_id"],
                        "departure_seconds": parse_gtfs_time(first["departure_time"]),
                        "arrival_seconds": parse_gtfs_time(second["arrival_time"]),
                    }
                )
        return result

    def route_geojson(self) -> dict[str, Any]:
        stops = {
            row["stop_id"]: (float(row["stop_lon"]), float(row["stop_lat"]))
            for row in self.files.get("stops.txt", [])
        }
        shapes: dict[str, list[tuple[float, float]]] = {}
        shape_rows = self.files.get("shapes.txt", [])
        for row in sorted(shape_rows, key=lambda item: (item.get("shape_id", ""), int(item.get("shape_pt_sequence", "0")))):
            shapes.setdefault(row["shape_id"], []).append((float(row["shape_pt_lon"]), float(row["shape_pt_lat"])))
        trip_to_shape = {row["trip_id"]: row.get("shape_id", "") for row in self.files.get("trips.txt", [])}
        route_by_trip = {row["trip_id"]: row["route_id"] for row in self.files.get("trips.txt", [])}
        route_features: dict[str, dict[str, Any]] = {}
        for trip_id, route_id in sorted(route_by_trip.items()):
            if route_id in route_features:
                continue
            stop_rows = [
                row
                for row in self.files.get("stop_times.txt", [])
                if row.get("trip_id") == trip_id
            ]
            stop_rows.sort(key=lambda item: int(item["stop_sequence"]))
            coordinates = shapes.get(trip_to_shape.get(trip_id, ""), [])
            fallback = "official_shape"
            if not coordinates:
                coordinates = [stops[row["stop_id"]] for row in stop_rows if row["stop_id"] in stops]
                fallback = "stop_polyline" if len(coordinates) >= 2 else "none"
            route_features[route_id] = {
                "type": "Feature",
                "id": f"{self.feed_id}:{route_id}",
                "properties": {
                    "route_id": route_id,
                    "feed_id": self.feed_id,
                    "shape_source": fallback,
                    "classification": "B",
                },
                "geometry": {"type": "LineString", "coordinates": coordinates},
            }
        return {"type": "FeatureCollection", "features": list(route_features.values())}
