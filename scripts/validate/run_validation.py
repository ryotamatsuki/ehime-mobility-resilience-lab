"""Run lightweight data-contract checks against the public bundle."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    public = ROOT / "web" / "data"
    required = ["manifest.json", "network.geojson", "population_zones.geojson", "metrics.json"]
    errors = []
    for name in required:
        path = public / name
        if not path.exists():
            errors.append(f"missing public artifact: {name}")
    for name in ["manifest.json", "metrics.json", "population_zones.geojson", "network.geojson"]:
        path = public / name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON {name}: {exc}")
            continue
        if name.endswith(".geojson") and data.get("type") != "FeatureCollection":
            errors.append(f"{name} is not a FeatureCollection")
    print(json.dumps({"status": "failed" if errors else "passed", "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
