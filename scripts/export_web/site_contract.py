"""Shared contracts for composing generated Planning Canvas capabilities.

Stage-specific exporters should describe their required artifacts and UI
capabilities, while this module owns repetitive file/HTML/manifest mechanics.
Keeping those mechanics in one place prevents successor stages from copying
fragile string-patching logic.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
RECOVERY_CARD_MARKER = '<article class="analytics-card recovery-card">'


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_paths(label: str, paths: Iterable[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"{label} requires: " + ", ".join(missing))


def ensure_stylesheet(html: str, asset: str) -> str:
    marker = f'href="{asset}"'
    if marker in html:
        return html
    if "</head>" not in html:
        raise ValueError("generated HTML has no </head> marker")
    return html.replace("</head>", f'  <link rel="stylesheet" href="{asset}">\n</head>', 1)


def ensure_script(html: str, asset: str) -> str:
    marker = f'src="{asset}"'
    if marker in html:
        return html
    if "</body>" not in html:
        raise ValueError("generated HTML has no </body> marker")
    return html.replace("</body>", f'  <script src="{asset}"></script>\n</body>', 1)


def set_ui_stage(html: str, stage: str, *, destination: str | None = None) -> str:
    """Set body UI metadata without depending on the previous stage value."""
    body_match = re.search(r"<body(?P<attrs>[^>]*)>", html, flags=re.IGNORECASE)
    if body_match is None:
        raise ValueError("generated HTML has no <body> element")
    attrs = body_match.group("attrs")
    if re.search(r'\bdata-ui-stage="[^"]*"', attrs):
        attrs = re.sub(r'\bdata-ui-stage="[^"]*"', f'data-ui-stage="{stage}"', attrs, count=1)
    else:
        attrs += f' data-ui-stage="{stage}"'
    if destination is not None:
        if re.search(r'\bdata-destination="[^"]*"', attrs):
            attrs = re.sub(
                r'\bdata-destination="[^"]*"',
                f'data-destination="{destination}"',
                attrs,
                count=1,
            )
        else:
            attrs += f' data-destination="{destination}"'
    replacement = f"<body{attrs}>"
    return html[: body_match.start()] + replacement + html[body_match.end() :]


def insert_before_recovery_card(html: str, fragment: str, *, identity_marker: str) -> str:
    if identity_marker in html:
        return html
    if RECOVERY_CARD_MARKER not in html:
        raise ValueError("generated HTML recovery-card insertion marker missing")
    return html.replace(RECOVERY_CARD_MARKER, fragment + RECOVERY_CARD_MARKER, 1)


def merge_manifest_capabilities(
    manifest_path: Path,
    *,
    result_stage: str,
    ui_release_stage: str,
    capabilities: Iterable[str],
    artifacts: Iterable[str] = (),
) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    if manifest.get("result_stage") != result_stage:
        raise ValueError(
            f"manifest result stage changed: expected {result_stage}, got {manifest.get('result_stage')}"
        )
    merged_capabilities = list(manifest.get("ui_capabilities") or [])
    for capability in capabilities:
        if capability not in merged_capabilities:
            merged_capabilities.append(capability)
    merged_artifacts = list(manifest.get("artifacts") or [])
    for artifact in artifacts:
        if artifact not in merged_artifacts:
            merged_artifacts.append(artifact)
    manifest["ui_capabilities"] = merged_capabilities
    manifest["artifacts"] = merged_artifacts
    manifest["analysis_result_stage"] = result_stage
    manifest["ui_release_stage"] = ui_release_stage
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def copy_web_assets(site: Path, assets: Iterable[str]) -> None:
    for asset in assets:
        source = ROOT / "web" / asset
        if not source.exists():
            raise FileNotFoundError(f"missing UI asset: {source}")
        shutil.copy2(source, site / asset)


def copy_docs(site: Path, names: Iterable[str]) -> None:
    output = site / "docs"
    output.mkdir(exist_ok=True)
    for name in names:
        source = ROOT / "docs" / name
        if source.exists():
            shutil.copy2(source, output / name)
