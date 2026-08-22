"""Helpers for verifying public OSM hospital points against an official registry.

The official workbook is used transiently as a verification source.  These
helpers deliberately return only the minimum internal fields needed to match
records.  Public facility geometry remains sourced from OSM so the workbook is
not republished through the GitHub Pages bundle.
"""
from __future__ import annotations

import io
import math
import re
import unicodedata
import zipfile
from typing import Any
from xml.etree import ElementTree as ET

SHEET_NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
PKG_NS = {"p": "http://schemas.openxmlformats.org/package/2006/relationships"}


def _column_index(reference: str) -> int:
    letters = "".join(ch for ch in reference if ch.isalpha()).upper()
    value = 0
    for ch in letters:
        value = value * 26 + (ord(ch) - ord("A") + 1)
    return max(0, value - 1)


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [
        "".join((text.text or "") for text in item.findall(".//m:t", SHEET_NS))
        for item in root.findall("m:si", SHEET_NS)
    ]


def _first_sheet_target(archive: zipfile.ZipFile) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relmap = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in relationships.findall("p:Relationship", PKG_NS)
    }
    sheet = workbook.find("m:sheets/m:sheet", SHEET_NS)
    if sheet is None:
        raise ValueError("official workbook has no worksheet")
    rid = sheet.attrib[f"{{{SHEET_NS['r']}}}id"]
    target = relmap[rid].lstrip("/")
    return target if target.startswith("xl/") else "xl/" + target


def _cell_value(cell: ET.Element, strings: list[str]) -> str:
    typ = cell.attrib.get("t")
    if typ == "inlineStr":
        return "".join((text.text or "") for text in cell.findall(".//m:t", SHEET_NS))
    value = cell.findtext("m:v", default="", namespaces=SHEET_NS)
    if typ == "s" and value:
        return strings[int(value)]
    return value


def workbook_records(payload: bytes) -> list[dict[str, str]]:
    """Read the first worksheet into dictionaries while preserving blank cells."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        strings = _shared_strings(archive)
        root = ET.fromstring(archive.read(_first_sheet_target(archive)))
        raw_rows: list[dict[int, str]] = []
        for row in root.findall(".//m:sheetData/m:row", SHEET_NS):
            values: dict[int, str] = {}
            for cell in row.findall("m:c", SHEET_NS):
                ref = cell.attrib.get("r", "A1")
                values[_column_index(ref)] = _cell_value(cell, strings).strip()
            if any(values.values()):
                raw_rows.append(values)
        if not raw_rows:
            return []
        header_row = raw_rows[0]
        headers = {index: value for index, value in header_row.items() if value}
        records: list[dict[str, str]] = []
        for row in raw_rows[1:]:
            record = {header: row.get(index, "") for index, header in headers.items()}
            if any(record.values()):
                records.append(record)
        return records


def official_hospitals(
    payload: bytes,
    bbox: tuple[float, float, float, float],
) -> list[dict[str, Any]]:
    """Return active hospital records within bbox for internal verification."""
    south, west, north, east = bbox
    hospitals: list[dict[str, Any]] = []
    for row in workbook_records(payload):
        if row.get("機関区分") != "1" or row.get("活動区分") != "活動中":
            continue
        try:
            lat = float(row.get("所在地座標（緯度）") or "nan")
            lon = float(row.get("所在地座標（経度）") or "nan")
        except ValueError:
            continue
        if not (math.isfinite(lat) and math.isfinite(lon)):
            continue
        if not (south <= lat <= north and west <= lon <= east):
            continue
        hospitals.append(
            {
                "official_id": row.get("機関コード", ""),
                "official_name": row.get("正式名称", ""),
                "short_name": row.get("略称", ""),
                "lat": lat,
                "lon": lon,
                "emergency_designated": row.get("救急告示医療機関", ""),
            }
        )
    return hospitals


def normalize_facility_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").lower()
    value = re.sub(r"[\s\u3000・･,，.。()（）\-ー]", "", value)
    for token in (
        "社会医療法人",
        "医療法人社団",
        "医療法人財団",
        "医療法人",
        "一般社団法人",
        "一般財団法人",
        "公益社団法人",
        "公益財団法人",
    ):
        value = value.replace(token, "")
    return value


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _name_compatible(osm_name: str, official: dict[str, Any]) -> bool:
    osm_norm = normalize_facility_name(osm_name)
    if not osm_norm or osm_norm == "hospital":
        return False
    candidates = {
        normalize_facility_name(str(official.get("official_name", ""))),
        normalize_facility_name(str(official.get("short_name", ""))),
    }
    candidates.discard("")
    for candidate in candidates:
        if osm_norm == candidate or osm_norm in candidate or candidate in osm_norm:
            return True
    return False


def verify_osm_hospitals(
    osm_facilities: list[dict[str, Any]],
    official: list[dict[str, Any]],
    *,
    named_max_km: float = 0.35,
    unnamed_max_km: float = 0.12,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Keep only OSM hospital points that can be verified against official records.

    Named points require spatial proximity plus compatible names.  Unnamed OSM
    hospital features are accepted only under a much tighter spatial threshold.
    Official identifiers/names are never copied into the returned public items.
    """
    verified: list[dict[str, Any]] = []
    used_official: set[int] = set()
    for facility in osm_facilities:
        name = str(facility.get("name", "") or "")
        ranked: list[tuple[float, int, dict[str, Any]]] = []
        for index, record in enumerate(official):
            distance = haversine_km(
                float(facility["lat"]),
                float(facility["lon"]),
                float(record["lat"]),
                float(record["lon"]),
            )
            ranked.append((distance, index, record))
        ranked.sort(key=lambda item: item[0])
        if not ranked:
            continue
        distance, official_index, record = ranked[0]
        named = bool(normalize_facility_name(name)) and normalize_facility_name(name) != "hospital"
        accepted = (
            named and distance <= named_max_km and _name_compatible(name, record)
        ) or (
            not named and distance <= unnamed_max_km
        )
        if not accepted:
            continue
        item = dict(facility)
        item["officially_verified"] = True
        item["verification_distance_km"] = round(distance, 4)
        # Do not copy official identifiers, names, addresses or coordinates.
        verified.append(item)
        used_official.add(official_index)
    stats = {
        "official_hospitals_in_envelope": len(official),
        "osm_hospitals_in_envelope": len(osm_facilities),
        "verified_osm_hospitals": len(verified),
        "unverified_osm_hospitals_excluded": len(osm_facilities) - len(verified),
        "official_records_with_osm_match": len(used_official),
        "official_records_without_osm_match": len(official) - len(used_official),
    }
    return verified, stats
