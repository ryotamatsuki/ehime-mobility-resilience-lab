"""Provenance and reproducibility helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(value: Any, length: int = 16) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()[:length]


def git_sha(repository: str | Path | None = None) -> str | None:
    try:
        command = ["git", "rev-parse", "HEAD"]
        result = subprocess.run(
            command,
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def generated_at_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def make_provenance(
    artifact_id: str,
    classification: str,
    model_version: str,
    input_data_versions: list[dict[str, Any]] | None,
    parameters: dict[str, Any],
    scenario_id: str | None = None,
    limitations: list[str] | None = None,
    repository: str | Path | None = None,
    random_seed: int | None = None,
) -> dict[str, Any]:
    if classification not in {"A", "B", "C", "D"}:
        raise ValueError("classification must be A, B, C, or D")
    return {
        "schema_version": "1.0.0",
        "artifact_id": artifact_id,
        "classification": classification,
        "input_data_versions": input_data_versions or [],
        "model_version": model_version,
        "scenario_id": scenario_id,
        "parameters": parameters,
        "generated_at_utc": generated_at_utc(),
        "git_sha": git_sha(repository),
        "random_seed": random_seed,
        "limitations": limitations or [],
    }
