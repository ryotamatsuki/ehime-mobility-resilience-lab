"""Build an A1.13 Planning Canvas from the protected A1.12 predecessor."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.export_web.apply_a1_12_ui import apply as apply_a1_12
from scripts.export_web.build_a1_12_site import build as build_a1_12_site
from scripts.export_web.site_contract import (
    merge_manifest_capabilities,
    read_json,
    require_paths,
)


def build(source: Path, destination: Path) -> dict:
    summary_path = source / "summary.json"
    robustness_path = source / "robustness_summary.json"
    cases_path = source / "robustness_cases.json"
    predecessor = source / "a1_12"
    require_paths(
        "A1.13 source",
        (
            summary_path,
            robustness_path,
            cases_path,
            predecessor / "summary.json",
            predecessor / "equity_summary.json",
            predecessor / "vulnerable_population_access.geojson",
        ),
    )
    summary = read_json(summary_path)
    robustness = read_json(robustness_path)
    predecessor_summary = read_json(predecessor / "summary.json")
    if summary.get("stage") != "A1.13" or robustness.get("stage") != "A1.13":
        raise ValueError("A1.13 source stage contract invalid")
    if predecessor_summary.get("stage") != "A1.12":
        raise ValueError("A1.13 protected predecessor must remain A1.12")

    build_a1_12_site(predecessor, destination)
    apply_a1_12(destination)

    data = destination / "data"
    shutil.copy2(summary_path, data / "summary.json")
    shutil.copy2(robustness_path, data / "robustness_summary.json")
    shutil.copy2(cases_path, data / "robustness_cases.json")
    manifest_path = data / "manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("result_stage") != "A1.12" or manifest.get("ui_release_stage") != "A1.12":
        raise ValueError("A1.13 expected completed A1.12 predecessor UI")

    # Explicitly promote the analysis result contract only after A1.12 site
    # composition has completed. This is not stage spoofing: summary.json is
    # already the real A1.13 result and the manifest is advanced to match it.
    manifest["result_stage"] = "A1.13"
    manifest["analysis_result_stage"] = "A1.13"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    merge_manifest_capabilities(
        manifest_path,
        result_stage="A1.13",
        ui_release_stage="A1.12",
        capabilities=(),
        artifacts=("robustness_summary.json", "robustness_cases.json"),
    )

    result = {
        "result_stage": "A1.13",
        "predecessor_result_stage": "A1.12",
        "predecessor_ui_stage": "A1.12",
        "destination": str(destination),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "outputs" / "a1_13")
    parser.add_argument("--destination", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    build(args.source, args.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
