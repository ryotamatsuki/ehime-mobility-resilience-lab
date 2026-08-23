"""Build an A1.12 Planning Canvas by composing verified UI capabilities."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.export_web.apply_a1_11_ui import apply as apply_a1_11
from scripts.export_web.build_a1_11_site import build as build_a1_11_site
from scripts.export_web.site_contract import (
    merge_manifest_capabilities,
    read_json,
    require_paths,
)


def build(source: Path, destination: Path) -> dict:
    summary_path = source / "summary.json"
    equity_path = source / "equity_summary.json"
    vulnerable_path = source / "vulnerable_population_access.geojson"
    require_paths("A1.12 source", (summary_path, equity_path, vulnerable_path))
    summary = read_json(summary_path)
    equity = read_json(equity_path)
    if summary.get("stage") != "A1.12" or equity.get("stage") != "A1.12":
        raise ValueError("A1.12 source stage contract invalid")

    # Compose capabilities without mutating summary.stage. The base exporter,
    # A1.10 destination UI and A1.11 time-criticality UI all preserve A1.12 as
    # the real analysis result stage.
    build_a1_11_site(source, destination)
    apply_a1_11(destination)

    data = destination / "data"
    shutil.copy2(equity_path, data / "equity_summary.json")
    shutil.copy2(vulnerable_path, data / "vulnerable_population_access.geojson")
    manifest_path = data / "manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("ui_release_stage") != "A1.11":
        raise ValueError("A1.12 expected A1.11 predecessor UI")
    merge_manifest_capabilities(
        manifest_path,
        result_stage="A1.12",
        ui_release_stage="A1.11",
        capabilities=(),
        artifacts=("equity_summary.json", "vulnerable_population_access.geojson"),
    )

    result = {
        "result_stage": "A1.12",
        "predecessor_ui_stage": "A1.11",
        "destination": str(destination),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "outputs" / "a1_12")
    parser.add_argument("--destination", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    build(args.source, args.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())