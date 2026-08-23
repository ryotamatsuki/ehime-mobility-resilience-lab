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


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(source: Path, destination: Path) -> dict:
    required = [source / "summary.json", source / "equity_summary.json", source / "vulnerable_population_access.geojson"]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("A1.12 source incomplete: " + ", ".join(missing))
    summary = read_json(source / "summary.json")
    equity = read_json(source / "equity_summary.json")
    if summary.get("stage") != "A1.12" or equity.get("stage") != "A1.12":
        raise ValueError("A1.12 source stage contract invalid")

    # Compose capabilities without mutating summary.stage. The base exporter,
    # A1.10 destination UI and A1.11 time-criticality UI all preserve A1.12 as
    # the real analysis result stage.
    build_a1_11_site(source, destination)
    apply_a1_11(destination)

    data = destination / "data"
    shutil.copy2(source / "equity_summary.json", data / "equity_summary.json")
    shutil.copy2(source / "vulnerable_population_access.geojson", data / "vulnerable_population_access.geojson")
    manifest_path = data / "manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("result_stage") != "A1.12":
        raise ValueError("A1.12 result-stage identity was lost while composing predecessor UI")
    if manifest.get("ui_release_stage") != "A1.11":
        raise ValueError("A1.12 expected A1.11 predecessor UI")
    artifacts = list(manifest.get("artifacts") or [])
    for name in ("equity_summary.json", "vulnerable_population_access.geojson"):
        if name not in artifacts:
            artifacts.append(name)
    manifest["artifacts"] = artifacts
    manifest["analysis_result_stage"] = "A1.12"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {"result_stage": "A1.12", "predecessor_ui_stage": "A1.11", "destination": str(destination)}
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