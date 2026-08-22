"""Run lightweight data-contract checks against the public bundle."""

from __future__ import annotations

import json
import gzip
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def read_public_json(public: Path, logical_name: str) -> object:
    plain = public / logical_name
    if plain.exists():
        return json.loads(plain.read_text(encoding="utf-8"))
    compressed = public / (logical_name + ".gz")
    if compressed.exists():
        with gzip.open(compressed, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    raise FileNotFoundError(logical_name)


def main() -> int:
    public = ROOT / "web" / "data"
    required = ["manifest.json", "network.geojson", "population_zones.geojson", "metrics.json"]
    errors = []
    loaded = {}
    for name in required:
        try:
            loaded[name] = read_public_json(public, name)
        except FileNotFoundError:
            errors.append(f"missing public artifact: {name}")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {name}: {exc}")
    for name, data in loaded.items():
        if name.endswith(".geojson") and data.get("type") != "FeatureCollection":
            errors.append(f"{name} is not a FeatureCollection")
    print(json.dumps({"status": "failed" if errors else "passed", "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
