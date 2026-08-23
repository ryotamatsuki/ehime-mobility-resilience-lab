"""Apply the A1.10 destination-switcher capability to a compatible generated site.

The UI layer depends on shelter/hospital accessibility artifacts, not on a
specific successor stage number. Result-stage identity is preserved in the
manifest so later A1 layers can compose without rewriting analysis metadata.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.export_web.site_contract import (
    copy_docs,
    copy_web_assets,
    ensure_script,
    ensure_stylesheet,
    merge_manifest_capabilities,
    read_json,
    require_paths,
    set_ui_stage,
)

ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_RESULT_STAGES = {"A1.9", "A1.11", "A1.12"}
A110_CAPABILITIES = [
    "destination-switcher",
    "shelter-map-layer",
    "destination-synchronized-metrics",
    "destination-synchronized-charts",
    "destination-provenance-popups",
]


def apply(site: Path) -> dict:
    data = site / "data"
    require_paths(
        "A1.10",
        [
            site / "index.html",
            site / "app.js",
            data / "summary.json",
            data / "manifest.json",
            data / "shelters.geojson",
            data / "shelter_accessibility.json",
            data / "shelter_population_access.geojson",
        ],
    )

    summary = read_json(data / "summary.json")
    result_stage = summary.get("stage")
    if result_stage not in SUPPORTED_RESULT_STAGES or summary.get("status") != "computed":
        raise ValueError("A1.10 requires a computed shelter-capable A1 result")
    shelter_access = summary.get("shelter_accessibility") or {}
    for kind in ("emergency", "general", "welfare"):
        if shelter_access.get(kind, {}).get("usable_destinations", 0) < 1:
            raise ValueError(f"A1.10 has no usable {kind} destination")

    manifest_path = data / "manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("result_stage") != result_stage:
        raise ValueError("A1.10 summary/manifest result-stage mismatch")

    copy_web_assets(site, ("a1_10.css", "a1_10_runtime.js"))
    index_path = site / "index.html"
    html = index_path.read_text(encoding="utf-8")
    html = ensure_stylesheet(html, "a1_10.css")
    html = ensure_script(html, "a1_10_runtime.js")
    html = set_ui_stage(html, "A1.10", destination="hospital")
    html = html.replace(
        "実GTFS・OSM・人口データで公共交通停止時の病院Accessibilityを比較する交通レジリエンス・プランニングキャンバス",
        "実GTFS・OSM・人口・公式避難所データで公共交通停止時の病院・避難所Accessibilityを比較する交通レジリエンス・プランニングキャンバス",
    )
    index_path.write_text(html, encoding="utf-8")

    merge_manifest_capabilities(
        manifest_path,
        result_stage=result_stage,
        ui_release_stage="A1.10",
        capabilities=A110_CAPABILITIES,
    )
    copy_docs(site, ("A1_10_DESTINATION_SWITCHER.md", "A1_10_QA_REPORT.md"))

    result = {
        "ui_release_stage": "A1.10",
        "result_stage": result_stage,
        "destinations": {
            "hospital": summary.get("osm", {}).get("hospital_destinations", 0),
            "emergency": shelter_access["emergency"]["usable_destinations"],
            "general": shelter_access["general"]["usable_destinations"],
            "welfare": shelter_access["welfare"]["usable_destinations"],
        },
        "capabilities_added": A110_CAPABILITIES,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    apply(args.site)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())