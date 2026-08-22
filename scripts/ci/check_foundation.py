"""A0-only repository checks.

This script deliberately checks structure and safety boundaries, not mobility
analysis. It is suitable for local execution and GitHub Actions without
external services or large datasets.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def fail(message: str) -> None:
    raise SystemExit(f"A0 foundation check failed: {message}")


def main() -> None:
    required = [
        ROOT / "README.md",
        ROOT / "docs" / "SPECIFICATION.md",
        ROOT / "docs" / "ARCHITECTURE.md",
        ROOT / "web" / "index.html",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))

    specification = (ROOT / "docs" / "SPECIFICATION.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

    for marker in ("Ehime Mobility Resilience Lab", "Phase A", "Decision Lock"):
        if marker not in specification:
            fail(f"specification marker not found: {marker}")
    for marker in ("Public Layer", "Analysis Layer", "Administration Layer", "GitHub Pages"):
        if marker not in architecture:
            fail(f"architecture marker not found: {marker}")
    if "docs/ARCHITECTURE.md" not in readme:
        fail("README does not link to docs/ARCHITECTURE.md")
    if "<title>" not in index or "Ehime Mobility Resilience Lab" not in index:
        fail("static Pages document is missing the product title")

    prohibited_fragments = (
        "new-earthquake",
        "earthquake-hazard",
        "hazard-derived",
        "hazard_derived",
    )
    implementation_roots = [
        ROOT / "src",
        ROOT / "admin",
        ROOT / "web",
    ]
    implementation_files = [
        path
        for directory in implementation_roots
        if directory.exists()
        for path in directory.rglob("*")
        if path.is_file() and path.suffix in {".py", ".js", ".ts", ".html", ".css"}
    ]
    tracked_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in implementation_files
    ).lower()
    for fragment in prohibited_fragments:
        if fragment in tracked_text:
            fail(f"Phase B implementation marker found: {fragment}")

    print("A0 foundation checks passed.")


if __name__ == "__main__":
    main()
