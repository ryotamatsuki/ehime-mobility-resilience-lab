"""Probe A1.1 external sources without persisting raw third-party data.

This script is intentionally small and dependency-free. It validates that the
selected real-world sources are reachable from CI and reports their structure
before the A1.1 ingestion pipeline is allowed to depend on them.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import urllib.parse
import urllib.request
import zipfile

GTFS_URL = "https://www.city.iyo.lg.jp/keizaikoyou/matidukuri/documents/agency.zip"
POP_URL = "https://gtfs-gis.jp/data/100m_pop2020/38/100m_mesh_pop2020_38210.zip"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

REQUIRED_GTFS = {"stops.txt", "routes.txt", "trips.txt", "stop_times.txt"}


def fetch(url: str, *, data: bytes | None = None, timeout: int = 90) -> bytes:
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
    raise RuntimeError("cannot decode text source")


def zip_members(payload: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        return sorted(name for name in archive.namelist() if not name.endswith("/"))


def zip_rows(payload: bytes, basename: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        matches = [name for name in archive.namelist() if name.rsplit("/", 1)[-1] == basename]
        if not matches:
            return []
        return list(csv.DictReader(io.StringIO(decode(archive.read(matches[0])))))


def first_csv(payload: bytes) -> tuple[str, list[dict[str, str]]]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        candidates = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not candidates:
            return "", []
        name = sorted(candidates)[0]
        return name, list(csv.DictReader(io.StringIO(decode(archive.read(name)))))


def probe_overpass() -> dict[str, object]:
    query = """
[out:json][timeout:60];
area["boundary"="administrative"]["name"="伊予市"]->.iyo;
(
  way(area.iyo)["highway"];
  node(area.iyo)["amenity"~"hospital|clinic|townhall|school"];
  way(area.iyo)["amenity"~"hospital|clinic|townhall|school"];
);
out count;
""".strip()
    payload = fetch(OVERPASS_URL, data=urllib.parse.urlencode({"data": query}).encode())
    response = json.loads(payload.decode("utf-8"))
    return {"elements": response.get("elements", [])}


def main() -> int:
    gtfs = fetch(GTFS_URL)
    gtfs_members = zip_members(gtfs)
    gtfs_basenames = {name.rsplit("/", 1)[-1] for name in gtfs_members}
    missing_gtfs = sorted(REQUIRED_GTFS - gtfs_basenames)
    stops = zip_rows(gtfs, "stops.txt")
    routes = zip_rows(gtfs, "routes.txt")
    trips = zip_rows(gtfs, "trips.txt")
    calendar = zip_rows(gtfs, "calendar.txt")
    calendar_dates = zip_rows(gtfs, "calendar_dates.txt")
    feed_info = zip_rows(gtfs, "feed_info.txt")

    population = fetch(POP_URL)
    population_members = zip_members(population)
    population_csv, population_rows = first_csv(population)
    population_header = list(population_rows[0]) if population_rows else []

    overpass = probe_overpass()

    report = {
        "gtfs": {
            "url": GTFS_URL,
            "bytes": len(gtfs),
            "members": gtfs_members,
            "missing_required": missing_gtfs,
            "stops": len(stops),
            "routes": len(routes),
            "trips": len(trips),
            "route_sample": routes[:3],
            "calendar": calendar[:5],
            "calendar_dates_tail": calendar_dates[-5:],
            "feed_info": feed_info[:3],
        },
        "population": {
            "url": POP_URL,
            "bytes": len(population),
            "members": population_members,
            "csv": population_csv,
            "row_count": len(population_rows),
            "header": population_header,
            "sample": population_rows[:5],
        },
        "osm": overpass,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if missing_gtfs:
        print("Selected GTFS source is not a complete static GTFS feed.", file=sys.stderr)
        return 2
    if not population_csv or not population_header:
        print("Population ZIP does not contain a readable CSV.", file=sys.stderr)
        return 3
    if not overpass.get("elements"):
        print("Overpass returned no summary elements.", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
