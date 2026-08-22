"""Build an A1.11 Planning Canvas without weakening predecessor contracts.

The stable base exporter and A1.10 postprocessor deliberately accept A1.9.
A1.11 therefore builds a temporary A1.9-compatible view from the freshly
computed successor output, passes the existing A1.9/A1.10 gates unchanged,
then restores the real A1.11 summary and manifest result stage before the
A1.11 UI postprocessor runs.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from scripts.export_web.apply_a1_10_ui import apply as apply_a1_10
from scripts.export_web.build_a1_2_demo import build as build_base


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(source: Path, destination: Path) -> dict:
    summary_path = source / "summary.json"
    td_path = source / "time_dependent_criticality.json"
    if not summary_path.exists() or not td_path.exists():
        raise FileNotFoundError("A1.11 source requires summary.json and time_dependent_criticality.json")
    summary = read_json(summary_path)
    td = read_json(td_path)
    if summary.get("stage") != "A1.11" or summary.get("status") != "computed":
        raise ValueError("A1.11 source summary contract invalid")
    if td.get("stage") != "A1.11" or len(td.get("rows") or []) != 16:
        raise ValueError("A1.11 time-dependent criticality contract invalid")

    with tempfile.TemporaryDirectory(prefix="a1_11_compat_") as raw_temp:
        compat = Path(raw_temp) / "a1_9_compat"
        shutil.copytree(source, compat)
        compat_summary_path = compat / "summary.json"
        compat_summary = read_json(compat_summary_path)
        compat_summary["stage"] = "A1.9"
        compat_summary["title"] = "大洲市 避難所 Accessibility / A1.11 predecessor view"
        compat_summary_path.write_text(json.dumps(compat_summary, ensure_ascii=False, indent=2), encoding="utf-8")

        build_base(compat, ROOT / "web", destination)
        # A1.10 is validated against the genuine predecessor-shaped view.
        apply_a1_10(destination)

    data = destination / "data"
    shutil.copy2(summary_path, data / "summary.json")
    shutil.copy2(td_path, data / "time_dependent_criticality.json")

    manifest_path = data / "manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("ui_release_stage") != "A1.10":
        raise ValueError("A1.11 expected A1.10 predecessor UI")
    manifest["result_stage"] = "A1.11"
    manifest["analysis_result_stage"] = "A1.11"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {
        "result_stage": "A1.11",
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
