"""Assemble the static GitHub Pages artifact from web/."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("web"))
    parser.add_argument("--destination", type=Path, default=Path("_site"))
    args = parser.parse_args()

    source = args.source.resolve()
    destination = args.destination.resolve()
    if not (source / "index.html").is_file():
        raise SystemExit(f"static source has no index.html: {source}")
    if destination == source or destination in source.parents:
        raise SystemExit("destination must not overwrite the static source")

    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    print(f"assembled {destination}")


if __name__ == "__main__":
    main()
