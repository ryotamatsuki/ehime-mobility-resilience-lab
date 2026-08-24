import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_a1_13_export_clis_start_directly():
    for script in (
        "scripts/export_web/build_a1_13_site.py",
        "scripts/export_web/apply_a1_13_ui.py",
    ):
        result = subprocess.run(
            [sys.executable, script, "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "--" in result.stdout
