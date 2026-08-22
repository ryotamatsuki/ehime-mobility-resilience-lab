"""Build the A1.2 static WebGIS from the verified A1.1 real-data outputs.

The source web directory contains only application code and legacy A0 fixtures.
This builder creates a clean deployable site and replaces the public data folder
with the current A1.1 derived outputs. Raw third-party input archives are never
copied into the site.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_RESULTS = (
    "summary.json",
    "stops.geojson",
    "facilities.geojson",
    "routes.geojson",
    "population_access.geojson",
)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_results(source: Path) -> dict:
    missing = [name for name in REQUIRED_RESULTS if not (source / name).exists()]
    if missing:
        raise FileNotFoundError("A1.1 result is incomplete: " + ", ".join(missing))

    summary = read_json(source / "summary.json")
    if summary.get("stage") != "A1.1" or summary.get("status") != "computed":
        raise ValueError("summary.json is not a completed A1.1 result")
    if summary.get("classification") != "C" or summary.get("scenario_classification") != "D":
        raise ValueError("A1.1 classification contract is invalid")
    if summary.get("gtfs", {}).get("snapped_stops") != summary.get("gtfs", {}).get("stops"):
        raise ValueError("not all GTFS stops are snapped to the walking network")
    if summary.get("osm", {}).get("hospital_destinations", 0) < 1:
        raise ValueError("A1.1 has no hospital destinations")
    if summary.get("population", {}).get("zones_in_envelope", 0) < 1:
        raise ValueError("A1.1 has no population zones")

    for name in ("stops.geojson", "facilities.geojson", "routes.geojson", "population_access.geojson"):
        payload = read_json(source / name)
        if payload.get("type") != "FeatureCollection" or not payload.get("features"):
            raise ValueError(f"{name} is not a non-empty FeatureCollection")
    return summary


def copy_static_web(web: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for item in web.iterdir():
        if item.name in {"data", "tests"}:
            continue
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def build(source: Path, web: Path, destination: Path) -> dict:
    summary = validate_results(source)
    copy_static_web(web, destination)

    data_dir = destination / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_RESULTS:
        shutil.copy2(source / name, data_dir / name)

    manifest = {
        "stage": "A1.2",
        "status": "computed",
        "title": "大洲市 ぐるりんおおず 病院Accessibility WebGIS",
        "result_stage": summary["stage"],
        "analysis_date": summary["analysis_date"],
        "departure_time": summary["departure_time"],
        "classification": summary["classification"],
        "scenario_classification": summary["scenario_classification"],
        "coverage": "大洲市ぐるりんおおず停留所bbox周辺",
        "datasets": summary.get("provenance", {}).get("input_data_versions", []),
        "model_version": summary.get("provenance", {}).get("model_version"),
        "scenario_id": summary.get("scenario", {}).get("id"),
        "artifacts": list(REQUIRED_RESULTS),
        "public_limitations": summary.get("provenance", {}).get("limitations", []),
    }
    (data_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    docs_out = destination / "docs"
    docs_out.mkdir(exist_ok=True)
    for name in (
        "A1_1_MINIMAL_ACCESSIBILITY.md",
        "A1_1_QA_REPORT.md",
        "A1_2_WEBGIS_DEMO.md",
        "A1_2_QA_REPORT.md",
        "DATA_LICENSES.md",
    ):
        src = ROOT / "docs" / name
        if src.exists():
            shutil.copy2(src, docs_out / name)

    print(json.dumps({
        "stage": "A1.2",
        "destination": str(destination),
        "gtfs_stops": summary["gtfs"]["stops"],
        "population_zones": summary["population"]["zones_in_envelope"],
        "hospital_destinations": summary["osm"]["hospital_destinations"],
        "affected_population": summary["impact"]["population_with_gt_1min_increase"],
    }, ensure_ascii=False, indent=2))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "outputs" / "a1_1")
    parser.add_argument("--web", type=Path, default=ROOT / "web")
    parser.add_argument("--destination", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    build(args.source, args.web, args.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
