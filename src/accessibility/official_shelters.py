"""A1.9 helpers for official Ozu shelter open data and OSM position matching.

The Ozu workbook is CC BY 4.0 and contains official facility names, addresses,
hazard eligibility / target users and capacities, but no coordinates. Geometry
is therefore attached only when a named OSM feature inside the current analysis
envelope can be matched unambiguously. Ambiguous and unmatched records are kept
out of accessibility calculations rather than silently geocoded or guessed.
"""
from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from difflib import SequenceMatcher
from typing import Any
from xml.etree import ElementTree as ET

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

SHELTER_SHEETS = {
    "指定緊急避難場所": "emergency",
    "指定一般避難所": "general",
    "指定福祉避難所": "welfare",
}


def _column_index(reference: str) -> int:
    letters = "".join(ch for ch in reference if ch.isalpha()).upper()
    value = 0
    for ch in letters:
        value = value * 26 + (ord(ch) - ord("A") + 1)
    return max(0, value - 1)


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    path = "xl/sharedStrings.xml"
    if path not in archive.namelist():
        return []
    root = ET.fromstring(archive.read(path))
    result: list[str] = []
    for item in root.findall(f"{{{MAIN_NS}}}si"):
        result.append("".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t")))
    return result


def _cell_value(cell: ET.Element, strings: list[str]) -> str:
    typ = cell.attrib.get("t")
    if typ == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{{{MAIN_NS}}}t"))
    value = cell.find(f"{{{MAIN_NS}}}v")
    if value is None or value.text is None:
        return ""
    if typ == "s":
        return strings[int(value.text)]
    return value.text


def _workbook_sheets(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall(f"{{{PKG_NS}}}Relationship")
    }
    parent = workbook.find(f"{{{MAIN_NS}}}sheets")
    if parent is None:
        return []
    result: list[tuple[str, str]] = []
    for sheet in list(parent):
        name = sheet.attrib.get("name", "").strip()
        rid = sheet.attrib.get(f"{{{REL_NS}}}id", "")
        target = targets.get(rid, "").lstrip("/")
        if target and not target.startswith("xl/"):
            target = "xl/" + target
        if target:
            result.append((name, target))
    return result


def _sheet_rows(archive: zipfile.ZipFile, path: str, strings: list[str]) -> list[list[str]]:
    root = ET.fromstring(archive.read(path))
    result: list[list[str]] = []
    for row in root.findall(f".//{{{MAIN_NS}}}sheetData/{{{MAIN_NS}}}row"):
        values: dict[int, str] = {}
        for cell in row.findall(f"{{{MAIN_NS}}}c"):
            index = _column_index(cell.attrib.get("r", "A1"))
            values[index] = _cell_value(cell, strings).strip()
        if not any(values.values()):
            continue
        width = max(values) + 1
        result.append([values.get(index, "") for index in range(width)])
    return result


def _clean_number(value: str) -> int | None:
    text = unicodedata.normalize("NFKC", value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def official_shelters(payload: bytes) -> dict[str, list[dict[str, Any]]]:
    """Parse the three official Ozu shelter sheets from the CC BY 4.0 workbook."""
    result: dict[str, list[dict[str, Any]]] = {value: [] for value in SHELTER_SHEETS.values()}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        strings = _shared_strings(archive)
        for raw_name, path in _workbook_sheets(archive):
            sheet_name = raw_name.strip()
            kind = SHELTER_SHEETS.get(sheet_name)
            if kind is None:
                continue
            rows = _sheet_rows(archive, path, strings)
            header_index = next(
                (
                    index
                    for index, row in enumerate(rows)
                    if len(row) >= 3 and row[0].strip() == "№" and "施設名" in row[1] and "住所" in row[2]
                ),
                None,
            )
            if header_index is None:
                raise ValueError(f"official shelter sheet has no recognized header: {sheet_name}")
            for row in rows[header_index + 1 :]:
                number = _clean_number(row[0] if row else "")
                if number is None:
                    continue
                values = row + [""] * max(0, 10 - len(row))
                record: dict[str, Any] = {
                    "official_id": f"{kind}:{number}",
                    "kind": kind,
                    "number": number,
                    "name": values[1].strip(),
                    "address": values[2].strip(),
                    "capacity": None,
                }
                if kind == "emergency":
                    record.update(
                        {
                            "hazards": {
                                "flood": values[3] == "●",
                                "landslide": values[4] == "●",
                                "storm_surge": values[5] == "●",
                                "earthquake": values[6] == "●",
                                "tsunami": values[7] == "●",
                                "large_fire": values[8] == "●",
                            },
                            "capacity": _clean_number(values[9]),
                        }
                    )
                elif kind == "general":
                    record.update({"phone": values[3].strip(), "capacity": _clean_number(values[4])})
                elif kind == "welfare":
                    record.update(
                        {
                            "target_users": values[3].strip(),
                            "phone": values[4].strip(),
                            "capacity": _clean_number(values[5]),
                        }
                    )
                if record["name"]:
                    result[kind].append(record)
    return result


def normalize_shelter_name(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "").lower()
    text = re.sub(r"[\s\u3000・･,，.。:：;；/／()（）\[\]【】「」『』\-‐‑–—]", "", text)
    return text


def normalize_address(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "").lower()
    text = text.replace("愛媛県", "").replace("大洲市", "")
    text = re.sub(r"[\s\u3000,，.。\-‐‑–—]", "", text)
    text = text.replace("番地の", "-").replace("番地", "-").replace("号", "")
    return text


def osm_named_candidates(overpass: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract named OSM point/centre candidates usable for shelter verification."""
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for element in overpass.get("elements", []):
        tags = element.get("tags") or {}
        name = tags.get("name") or tags.get("name:ja")
        if not name:
            continue
        # Roads and ordinary commercial POIs are intentionally excluded.
        relevant = bool(
            tags.get("amenity")
            or tags.get("leisure")
            or tags.get("building")
            or tags.get("office") == "government"
            or tags.get("tourism")
        )
        if not relevant:
            continue
        if element.get("type") == "node" and "lat" in element and "lon" in element:
            lat, lon = float(element["lat"]), float(element["lon"])
        elif isinstance(element.get("center"), dict):
            lat, lon = float(element["center"]["lat"]), float(element["center"]["lon"])
        else:
            geometry = element.get("geometry") or []
            if not geometry:
                continue
            lat = sum(float(point["lat"]) for point in geometry) / len(geometry)
            lon = sum(float(point["lon"]) for point in geometry) / len(geometry)
        osm_id = f"osm:{element.get('type')}:{element.get('id')}"
        if osm_id in seen:
            continue
        seen.add(osm_id)
        address = (
            tags.get("addr:full")
            or "".join(
                str(tags.get(key, ""))
                for key in ("addr:province", "addr:city", "addr:suburb", "addr:quarter", "addr:street", "addr:housenumber")
            )
        )
        result.append(
            {
                "id": osm_id,
                "name": str(name),
                "address": str(address or ""),
                "lat": lat,
                "lon": lon,
                "amenity": tags.get("amenity"),
                "leisure": tags.get("leisure"),
                "building": tags.get("building"),
                "office": tags.get("office"),
            }
        )
    return result


def _match_score(record: dict[str, Any], candidate: dict[str, Any]) -> tuple[float, str]:
    official = normalize_shelter_name(str(record.get("name", "")))
    osm = normalize_shelter_name(str(candidate.get("name", "")))
    if len(official) < 3 or len(osm) < 3:
        return 0.0, "none"
    if official == osm:
        score, method = 1.0, "exact_name"
    elif len(osm) >= 4 and osm in official:
        score, method = 0.96, "osm_name_in_official"
    elif len(official) >= 4 and official in osm:
        score, method = 0.94, "official_name_in_osm"
    else:
        ratio = SequenceMatcher(None, official, osm).ratio()
        if ratio < 0.90:
            return 0.0, "none"
        score, method = ratio, "high_similarity_name"

    official_address = normalize_address(str(record.get("address", "")))
    osm_address = normalize_address(str(candidate.get("address", "")))
    if official_address and osm_address and (
        official_address in osm_address or osm_address in official_address
    ):
        score = min(1.0, score + 0.02)
        method += "+address"
    return score, method


def match_official_shelters(
    official: dict[str, list[dict[str, Any]]],
    candidates: list[dict[str, Any]],
    *,
    minimum_score: float = 0.90,
    ambiguity_margin: float = 0.03,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """One-to-one, name-led shelter matching with an explicit ambiguity gate."""
    matched: dict[str, list[dict[str, Any]]] = {kind: [] for kind in official}
    used_candidates: set[str] = set()
    stats: dict[str, Any] = {"by_kind": {}}

    for kind, records in official.items():
        unmatched = 0
        ambiguous = 0
        for record in records:
            scored: list[tuple[float, str, dict[str, Any]]] = []
            for candidate in candidates:
                if candidate["id"] in used_candidates:
                    continue
                score, method = _match_score(record, candidate)
                if score >= minimum_score:
                    scored.append((score, method, candidate))
            scored.sort(key=lambda item: (-item[0], str(item[2]["id"])))
            if not scored:
                unmatched += 1
                continue
            if len(scored) > 1 and scored[0][0] - scored[1][0] < ambiguity_margin:
                ambiguous += 1
                continue
            score, method, candidate = scored[0]
            item = dict(record)
            item.update(
                {
                    "id": record["official_id"],
                    "lat": float(candidate["lat"]),
                    "lon": float(candidate["lon"]),
                    "osm_id": candidate["id"],
                    "osm_name": candidate["name"],
                    "location_match_score": round(score, 4),
                    "location_match_method": method,
                    "location_source": "OpenStreetMap",
                }
            )
            matched[kind].append(item)
            used_candidates.add(candidate["id"])
        stats["by_kind"][kind] = {
            "official_records": len(records),
            "matched_records": len(matched[kind]),
            "unmatched_records": unmatched,
            "ambiguous_records": ambiguous,
        }

    stats["official_records"] = sum(len(records) for records in official.values())
    stats["matched_records"] = sum(len(records) for records in matched.values())
    stats["candidate_features"] = len(candidates)
    stats["matched_candidate_features"] = len(used_candidates)
    return matched, stats
