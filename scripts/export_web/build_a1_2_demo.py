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
SUPPORTED_RESULT_STAGES = {"A1.1", "A1.5", "A1.6"}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_results(source: Path) -> dict:
    missing = [name for name in REQUIRED_RESULTS if not (source / name).exists()]
    if missing:
        raise FileNotFoundError("A1 result is incomplete: " + ", ".join(missing))

    summary = read_json(source / "summary.json")
    stage = summary.get("stage")
    if stage not in SUPPORTED_RESULT_STAGES or summary.get("status") != "computed":
        raise ValueError("summary.json is not a completed supported A1 result")
    if summary.get("classification") != "C" or summary.get("scenario_classification") != "D":
        raise ValueError("A1 classification contract is invalid")
    if summary.get("gtfs", {}).get("snapped_stops") != summary.get("gtfs", {}).get("stops"):
        raise ValueError("not all GTFS stops are snapped to the walking network")
    if summary.get("osm", {}).get("hospital_destinations", 0) < 1:
        raise ValueError("A1 has no hospital destinations")
    if stage in {"A1.5", "A1.6"}:
        registry = summary.get("official_registry", {})
        if registry.get("verified_osm_hospitals", 0) < 1:
            raise ValueError(f"{stage} has no official-registry-verified OSM hospitals")
        if registry.get("official_records_without_osm_match", 1) != 0:
            raise ValueError(f"{stage} official hospitals are not fully represented by verified public OSM features")
        if registry.get("raw_workbook_published") is not False:
            raise ValueError(f"{stage} must not publish the raw official workbook")
    if stage == "A1.6":
        transfer = summary.get("transfer_network", {})
        if transfer.get("directed_edges", 0) < 1:
            raise ValueError("A1.6 has no generated walking transfer edges")
        if transfer.get("recursive_walking_transfer_chaining") is not False:
            raise ValueError("A1.6 recursive walking transfer chaining must remain disabled")
    if summary.get("population", {}).get("zones_in_envelope", 0) < 1:
        raise ValueError("A1 has no population zones")

    for name in ("stops.geojson", "facilities.geojson", "routes.geojson", "population_access.geojson"):
        payload = read_json(source / name)
        if payload.get("type") != "FeatureCollection" or not payload.get("features"):
            raise ValueError(f"{name} is not a non-empty FeatureCollection")
    facilities = read_json(source / "facilities.geojson")
    if stage in {"A1.5", "A1.6"}:
        if not all((feature.get("properties") or {}).get("officially_verified") is True for feature in facilities["features"]):
            raise ValueError(f"public {stage} facilities contain an unverified hospital")
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


def apply_result_specific_labels(destination: Path, summary: dict) -> None:
    stage = summary.get("stage")
    if stage not in {"A1.5", "A1.6"}:
        return
    index = destination / "index.html"
    html = index.read_text(encoding="utf-8")
    html = html.replace(
        "道路・病院：OpenStreetMap（B）",
        "道路・病院位置：OpenStreetMap（B）／病院照合：愛媛県公式台帳（A）",
    )
    if stage == "A1.6":
        html = html.replace(
            "<div><dt>分析範囲</dt><dd>GTFS停留所bbox周辺</dd></div>",
            "<div><dt>徒歩乗換</dt><dd>道路NW 10分以内 + 1分</dd></div><div><dt>分析範囲</dt><dd>GTFS停留所bbox周辺</dd></div>",
        )
    index.write_text(html, encoding="utf-8")

    app_path = destination / "app.js"
    app = app_path.read_text(encoding="utf-8")
    app = app.replace(
        "OpenStreetMap amenity=hospital（B）",
        "OpenStreetMap位置・名称（B）／愛媛県公式台帳照合済み（A）",
    )
    app_path.write_text(app, encoding="utf-8")


def build(source: Path, web: Path, destination: Path) -> dict:
    summary = validate_results(source)
    copy_static_web(web, destination)
    apply_result_specific_labels(destination, summary)

    data_dir = destination / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_RESULTS:
        shutil.copy2(source / name, data_dir / name)

    capabilities = [
        "three-pane-planning-canvas",
        "baseline-vs-disruption",
        "map-driven-scenario-selection",
        "mesh-before-after",
        "weighted-travel-time-distribution",
        "single-validated-recovery-action",
        "provenance-and-limitations",
    ]
    if summary["stage"] in {"A1.5", "A1.6"}:
        capabilities.append("official-hospital-verification-gate")
    else:
        capabilities.append("osm-hospital-destinations")
    if summary["stage"] == "A1.6":
        capabilities.extend(
            [
                "stop-to-stop-walking-transfer",
                "same-input-no-transfer-model-comparison",
            ]
        )

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
        "ui_capabilities": capabilities,
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
        "A1_6_WALKING_TRANSFER.md",
        "A1_6_QA_REPORT.md",
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
                "transfer_edges": summary.get("transfer_network", {}).get("directed_edges", 0),
                "affected_population": summary["impact"]["population_with_gt_1min_increase"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "outputs" / "a1_6")
    parser.add_argument("--web", type=Path, default=ROOT / "web")
    parser.add_argument("--destination", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    build(args.source, args.web, args.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
