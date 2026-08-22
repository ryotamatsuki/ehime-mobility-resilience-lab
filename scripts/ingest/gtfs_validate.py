"""Validate a GTFS ZIP supplied as an external input."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from transit.gtfs import GTFSFeed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path")
    parser.add_argument("--feed-id", default="external")
    args = parser.parse_args()
    feed = GTFSFeed.from_zip(args.zip_path, args.feed_id)
    errors = feed.validate()
    print(json.dumps({"feed_id": feed.feed_id, "errors": errors, "status": "failed" if errors else "passed"}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
