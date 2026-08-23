"""Build a Planning Canvas with the A1.11 time-criticality capability.

The base exporter validates successor result stages directly. This layer adds
A1.11 artifacts/capabilities while preserving the real analysis result stage.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.export_web.apply_a1_10_ui import apply as apply_a1_10
from scripts.export_web.build_a1_2_demo import build as build_base
from scripts.export_web.site_contract import (
    merge_manifest_capabilities,
    read_json,
    require_paths,
)

SUPPORTED_RESULT_STAGES = {"A1.11", "A1.12"}


def build(source: Path, destination: Path) -> dict:
    summary_path = source / "summary.json"
    td_path = source / "time_dependent_criticality.json"
    require_paths("A1.11 capability", (summary_path, td_path))
    summary = read_json(summary_path)
    td = read_json(td_path)
    result_stage = summary.get("stage")
    if result_stage not in SUPPORTED_RESULT_STAGES or summary.get("status") != "computed":
        raise ValueError("A1.11 capability requires a computed A1.11/A1.12 result")
    if td.get("stage") != "A1.11" or len(td.get("rows") or []) != 16:
        raise ValueError("A1.11 time-dependent criticality contract invalid")

    build_base(source, ROOT / "web", destination)
    apply_a1_10(destination)

    data = destination / "data"
    shutil.copy2(td_path, data / "time_dependent_criticality.json")
    manifest_path = data / "manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("ui_release_stage") != "A1.10":
        raise ValueError("A1.11 expected A1.10 predecessor UI")
    merge_manifest_capabilities(
        manifest_path,
        result_stage=result_stage,
        ui_release_stage="A1.10",
        capabilities=(),
        artifacts=("time_dependent_criticality.json",),
    )

    result = {
        "result_stage": result_stage,
        "predecessor_ui_stage": "A1.10",
        "slots": len(td["rows"]),
        "destination": str(destination),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "outputs" / "a1_11")
    parser.add_argument("--destination", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    build(args.source, args.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())