from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_ui_apply_scripts_support_direct_cli_execution() -> None:
    for relative in (
        "scripts/export_web/apply_a1_10_ui.py",
        "scripts/export_web/apply_a1_11_ui.py",
        "scripts/export_web/apply_a1_12_ui.py",
    ):
        result = subprocess.run(
            [sys.executable, relative, "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{relative} failed direct CLI startup: {result.stderr}"
        assert "--site" in result.stdout
