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


def zip_members(payload: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        return sorted(name for name in archive.namelist() if not name.endswith("/"))


def first_csv_header(payload: bytes) -> tuple[str, list[str]]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        candidates = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not candidates:
            return "", []
        name = sorted(candidates)[0]
        raw = archive.read(name)
        for encoding in ("utf-8-sig", "cp932", "shift_jis"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise RuntimeError(f"cannot decode {name}")
        reader = csv.reader(io.StringIO(text))
        return name, next(reader, [])


def probe_overpass() -> dict[str, object]:
    query = """
[out:json][timeout:60];
(
  way["highway"](33.65,132.55,33.86,132.86);
  node["amenity"~"hospital|clinic|townhall|school"](33.65,132.55,33.86,132.86);
  way["amenity"~"hospital|clinic|townhall|school"](33.65,132.55,33.86,132.86);
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

    population = fetch(POP_URL)
    population_members = zip_members(population)
    population_csv, population_header = first_csv_header(population)

    overpass = probe_overpass()

    report = {
        "gtfs": {
            "url": GTFS_URL,
            "bytes": len(gtfs),
            "members": gtfs_members,
            "missing_required": missing_gtfs,
        },
        "population": {
            "url": POP_URL,
            "bytes": len(population),
            "members": population_members,
            "csv": population_csv,
            "header": population_header,
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
