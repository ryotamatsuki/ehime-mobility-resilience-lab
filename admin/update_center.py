"""Safe candidate, validation, approval, and rollback operations."""

from __future__ import annotations

import csv
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.provenance import sha256_file


SUPPORTED_FORMATS = {"gtfs_zip", "csv", "xlsx", "geojson", "shapefile_zip", "geopackage"}
MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_ZIP_MEMBERS = 10000
MAX_ZIP_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024


def _safe_zip_members(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ZIP_MEMBERS:
            raise ValueError("archive contains too many members")
        total = 0
        names = []
        for info in infos:
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or any(part == ".." for part in Path(name).parts):
                raise ValueError(f"unsafe archive member: {name}")
            total += info.file_size
            if total > MAX_ZIP_UNCOMPRESSED_BYTES:
                raise ValueError("archive exceeds uncompressed size limit")
            names.append(name)
        return names


def detect_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix == ".xlsx":
        return "xlsx"
    if suffix in {".geojson", ".json"}:
        return "geojson"
    if suffix in {".gpkg", ".geopackage"}:
        return "geopackage"
    if suffix == ".zip":
        names = _safe_zip_members(path)
        if "stops.txt" in {Path(name).name for name in names}:
            return "gtfs_zip"
        if any(name.lower().endswith(".shp") for name in names):
            return "shapefile_zip"
        raise ValueError("ZIP is neither a GTFS feed nor a Shapefile archive")
    raise ValueError(f"unsupported file extension: {suffix}")


def validate_upload(path: str | Path, declared_format: str | None = None) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("file exceeds maximum size")
    format_name = declared_format or detect_format(source)
    if format_name not in SUPPORTED_FORMATS:
        raise ValueError(f"unsupported format: {format_name}")
    errors: list[str] = []
    warnings: list[str] = []
    if format_name == "csv":
        with source.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            rows = csv.reader(handle)
            header = next(rows, [])
            if not header:
                errors.append("CSV header is empty")
            if len(header) != len(set(header)):
                errors.append("CSV header contains duplicate columns")
    elif format_name == "geojson":
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
            if data.get("type") not in {"FeatureCollection", "Feature", "GeometryCollection"}:
                errors.append("unsupported GeoJSON top-level type")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid GeoJSON: {exc}")
    elif format_name in {"gtfs_zip", "shapefile_zip", "xlsx"}:
        names = _safe_zip_members(source)
        if format_name == "gtfs_zip":
            required = {"agency.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt"}
            available = {Path(name).name for name in names}
            for missing in sorted(required - available):
                errors.append(f"GTFS required file missing: {missing}")
    elif format_name == "geopackage":
        with source.open("rb") as handle:
            if handle.read(16) != b"SQLite format 3\x00":
                errors.append("GeoPackage does not have a SQLite header")
    if format_name in {"xlsx", "shapefile_zip"}:
        warnings.append("schema and CRS require format-specific inspection before approval")
    return {
        "path": str(source),
        "format": format_name,
        "size_bytes": source.stat().st_size,
        "checksum": sha256_file(source),
        "validation_status": "failed" if errors else "passed",
        "errors": errors,
        "warnings": warnings,
    }


class DataUpdateCenter:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.staging = self.root / "data" / "staging"
        self.metadata_path = self.root / "data" / "metadata" / "dataset_versions.json"
        self.staging.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_versions(self) -> list[dict[str, Any]]:
        if not self.metadata_path.exists():
            return []
        return json.loads(self.metadata_path.read_text(encoding="utf-8"))

    def _write_versions(self, versions: list[dict[str, Any]]) -> None:
        self.metadata_path.write_text(
            json.dumps(versions, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def stage(self, dataset_id: str, source: str | Path, reference_date: str, license_name: str) -> dict[str, Any]:
        source_path = Path(source)
        validation = validate_upload(source_path)
        version_id = f"{dataset_id}-{validation['checksum'][:12]}"
        destination = self.staging / version_id / source_path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        record = {
            "dataset_id": dataset_id,
            "dataset_name": dataset_id,
            "source": str(source_path),
            "license": license_name,
            "reference_date": reference_date,
            "imported_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "checksum": validation["checksum"],
            "schema_version": "1.0.0",
            "validation_status": validation["validation_status"],
            "status": "validated" if validation["validation_status"] == "passed" else "candidate",
            "version_id": version_id,
            "staged_path": str(destination.relative_to(self.root)),
            "validation": validation,
        }
        versions = [item for item in self._read_versions() if item.get("version_id") != version_id]
        versions.append(record)
        self._write_versions(versions)
        return record

    def approve(self, version_id: str) -> dict[str, Any]:
        versions = self._read_versions()
        selected = next((item for item in versions if item.get("version_id") == version_id), None)
        if selected is None:
            raise KeyError(version_id)
        if selected.get("validation_status") != "passed":
            raise ValueError("only a passed candidate can become active")
        for item in versions:
            if item.get("dataset_id") == selected["dataset_id"] and item.get("status") == "active":
                item["status"] = "archived"
        selected["status"] = "active"
        self._write_versions(versions)
        return selected

    def rollback(self, dataset_id: str, version_id: str) -> dict[str, Any]:
        versions = self._read_versions()
        selected = next(
            (
                item
                for item in versions
                if item.get("dataset_id") == dataset_id and item.get("version_id") == version_id
            ),
            None,
        )
        if selected is None:
            raise KeyError(version_id)
        if selected.get("validation_status") != "passed":
            raise ValueError("cannot rollback to a failed version")
        for item in versions:
            if item.get("dataset_id") == dataset_id:
                item["status"] = "active" if item is selected else "archived"
        self._write_versions(versions)
        return selected

    def list_versions(self, dataset_id: str | None = None) -> list[dict[str, Any]]:
        versions = self._read_versions()
        if dataset_id is None:
            return versions
        return [item for item in versions if item.get("dataset_id") == dataset_id]
