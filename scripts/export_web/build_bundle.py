"""Validate and report the static public bundle."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from common.provenance import sha256_file


def main() -> int:
    public = ROOT / "web" / "data"
    manifest_path = public / "manifest.json"
    if not manifest_path.exists():
        print("public bundle is missing; run scripts/build_network/build_public.py first")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest.get("artifacts", []):
        path = public / artifact["path"]
        if not path.exists() and path.suffix == ".gz":
            local_fallback = public / path.stem
            if local_fallback.exists():
                path = local_fallback
        if not path.exists():
            print(f"missing: {path}")
            return 1
        print(f"{artifact['path']}: {sha256_file(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
