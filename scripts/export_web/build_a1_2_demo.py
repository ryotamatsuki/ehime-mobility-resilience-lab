"""Build the planning-canvas WebGIS from verified A1 real-data outputs.

The source web directory contains application code and legacy fixtures. This
builder creates a clean deployable site and replaces the public data folder with
current derived outputs. Raw third-party input archives are never copied to the
public site.
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
SUPPORTED_RESULT_STAGES = {"A1.1", "A1.5"}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_results(source: Path) -> dict:
    missing = [name for name in REQUIRED_RESULTS if not (source / name).exists()]
    if missing:
        raise FileNotFoundError("A1 result is incomplete: " + ", ".join(missing))

    summary = read_json(source / "summary.json")
    if summary.get("stage") not in SUPPORTED_RESULT_STAGES or summary.get("status") != "computed":
        raise ValueError("summary.json is not a completed supported A1 result")
    if summary.get("classification") != "C" or summary.get("scenario_classification") != "D":
        raise ValueError("A1 classification contract is invalid")
    if summary.get("gtfs", {}).get("snapped_stops") != summary.get("gtfs", {}).get("stops"):
        raise ValueError("not all GTFS stops are snapped to the walking network")
    if summary.get("osm", {}).get("hospital_destinations", 0) < 1:
        raise ValueError("A1 has no hospital destinations")
    if summary.get("stage") == "A1.5":
        registry = summary.get("official_registry", {})
        if registry.get("verified_osm_hospitals", 0) < 1:
            raise ValueError("A1.5 has no official-registry-verified OSM hospitals")
        if registry.get("raw_workbook_published") is not False:
            raise ValueError("A1.5 must not publish the raw official workbook")
    if summary.get("population", {}).get("zones_in_envelope", 0) < 1:
        raise ValueError("A1 has no population zones")

    for name in ("stops.geojson", "facilities.geojson", "routes.geojson", "population_access.geojson"):
        payload = read_json(source / name)
        if payload.get("type") != "FeatureCollection" or not payload.get("features"):
            raise ValueError(f"{name} is not a non-empty FeatureCollection")
    facilities = read_json(source / "facilities.geojson")
    if summary.get("stage") == "A1.5":
        if not all((feature.get("properties") or {}).get("officially_verified") is True for feature in facilities["features"]):
            raise ValueError("public A1.5 facilities contain an unverified hospital")
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
        "stage": "A1.3",
        "status": "computed",
        "title": "Ehime Mobility Resilience Lab — Planning Canvas",
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
        "ui_capabilities": [
            "three-pane-planning-canvas",
            "baseline-vs-disruption",
            "map-driven-scenario-selection",
            "mesh-before-after",
            "weighted-travel-time-distribution",
            "single-validated-recovery-action",
            "provenance-and-limitations",
            "official-hospital-verification-gate" if summary["stage"] == "A1.5" else "osm-hospital-destinations",
        ],
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
        "A1_3_IDEAL_UI.md",
        "A1_3_QA_REPORT.md",
        "A1_4_MOBILE_UX.md",
        "A1_4_QA_REPORT.md",
        "A1_5_OFFICIAL_HOSPITAL_GATE.md",
        "A1_5_QA_REPORT.md",
        "DATA_LICENSES.md",
    ):
        src = ROOT / "docs" / name
        if src.exists():
            shutil.copy2(src, docs_out / name)

    print(
        json.dumps(
            {
                "stage": "A1.3",
                "result_stage": summary["stage"],
                "destination": str(destination),
                "gtfs_stops": summary["gtfs"]["stops"],
                "population_zones": summary["population"]["zones_in_envelope"],
                "hospital_destinations": summary["osm"]["hospital_destinations"],
                "affected_population": summary["impact"]["population_with_gt_1min_increase"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "outputs" / "a1_5")
    parser.add_argument("--web", type=Path, default=ROOT / "web")
    parser.add_argument("--destination", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    build(args.source, args.web, args.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
