"""Apply the A1.10 destination-switcher UI to a generated A1.9 site.

This postprocessor intentionally runs after the A1.9 generated-site regression
smoke test. It does not change routing outputs or accessibility values; it only
adds UI assets, metadata and documentation that expose already-computed A1.9
hospital/shelter destinations consistently.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A110_CAPABILITIES = [
    "destination-switcher",
    "shelter-map-layer",
    "destination-synchronized-metrics",
    "destination-synchronized-charts",
    "destination-provenance-popups",
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def apply(site: Path) -> dict:
    data = site / "data"
    required = [
        site / "index.html",
        site / "app.js",
        data / "summary.json",
        data / "manifest.json",
        data / "shelters.geojson",
        data / "shelter_accessibility.json",
        data / "shelter_population_access.geojson",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("A1.10 requires a complete generated A1.9 site: " + ", ".join(missing))

    summary = read_json(data / "summary.json")
    if summary.get("stage") != "A1.9" or summary.get("status") != "computed":
        raise ValueError("A1.10 must be applied to a computed A1.9 result")
    shelter_access = summary.get("shelter_accessibility") or {}
    for kind in ("emergency", "general", "welfare"):
        if shelter_access.get(kind, {}).get("usable_destinations", 0) < 1:
            raise ValueError(f"A1.10 has no usable {kind} destination")

    for asset in ("a1_10.css", "a1_10_runtime.js"):
        src = ROOT / "web" / asset
        if not src.exists():
            raise FileNotFoundError(f"missing A1.10 UI asset: {src}")
        shutil.copy2(src, site / asset)

    index_path = site / "index.html"
    html = index_path.read_text(encoding="utf-8")
    if 'href="a1_10.css"' not in html:
        html = html.replace('</head>', '  <link rel="stylesheet" href="a1_10.css">\n</head>', 1)
    if 'src="a1_10_runtime.js"' not in html:
        html = html.replace('</body>', '  <script src="a1_10_runtime.js"></script>\n</body>', 1)
    if '<body data-ui-stage="A1.10"' not in html:
        html = html.replace('<body>', '<body data-ui-stage="A1.10" data-destination="hospital">', 1)
    html = html.replace(
        '実GTFS・OSM・人口データで公共交通停止時の病院Accessibilityを比較する交通レジリエンス・プランニングキャンバス',
        '実GTFS・OSM・人口・公式避難所データで公共交通停止時の病院・避難所Accessibilityを比較する交通レジリエンス・プランニングキャンバス',
    )
    index_path.write_text(html, encoding="utf-8")

    manifest_path = data / "manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("result_stage") != "A1.9":
        raise ValueError("A1.10 manifest result_stage must remain A1.9")
    manifest["ui_release_stage"] = "A1.10"
    capabilities = list(manifest.get("ui_capabilities") or [])
    for capability in A110_CAPABILITIES:
        if capability not in capabilities:
            capabilities.append(capability)
    manifest["ui_capabilities"] = capabilities
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    docs_out = site / "docs"
    docs_out.mkdir(exist_ok=True)
    for name in ("A1_10_DESTINATION_SWITCHER.md", "A1_10_QA_REPORT.md"):
        src = ROOT / "docs" / name
        if src.exists():
            shutil.copy2(src, docs_out / name)

    result = {
        "ui_release_stage": "A1.10",
        "result_stage": "A1.9",
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
