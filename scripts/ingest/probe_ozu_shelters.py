"""Probe the official Ozu shelter open-data workbook without persisting it.

The workbook is CC BY 4.0 open data. This probe intentionally logs only compact
sheet/schema information needed to design the A1.9 parser; the downloaded XLSX
exists only in memory.
"""
from __future__ import annotations

import io
import json
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

URL = "https://www.city.ozu.ehime.jp/uploaded/attachment/47130.xlsx"
LANDING = "https://www.city.ozu.ehime.jp/site/opendata/31903.html"
NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def fetch() -> bytes:
    req = urllib.request.Request(
        URL,
        headers={"User-Agent": "EhimeMobilityResilienceLab/1.0 (+public-data-validation)"},
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        payload = response.read()
    if not payload.startswith(b"PK"):
        raise ValueError("official shelter resource is not an XLSX/ZIP payload")
    return payload


def shared_strings(zf: zipfile.ZipFile) -> list[str]:
    path = "xl/sharedStrings.xml"
    if path not in zf.namelist():
        return []
    root = ET.fromstring(zf.read(path))
    result = []
    for si in root.findall(f"{{{NS_MAIN}}}si"):
        parts = [node.text or "" for node in si.iter(f"{{{NS_MAIN}}}t")]
        result.append("".join(parts))
    return result


def workbook_sheets(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall(f"{{{NS_PKG}}}Relationship")
    }
    sheets = []
    for sheet in wb.find(f"{{{NS_MAIN}}}sheets") or []:
        name = sheet.attrib.get("name", "")
        rid = sheet.attrib.get(f"{{{NS_REL}}}id", "")
        target = targets[rid]
        if not target.startswith("xl/"):
            target = "xl/" + target.lstrip("/")
        sheets.append((name, target))
    return sheets


def cell_value(cell: ET.Element, strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{{{NS_MAIN}}}t"))
    value = cell.find(f"{{{NS_MAIN}}}v")
    if value is None or value.text is None:
        return ""
    if cell_type == "s":
        return strings[int(value.text)]
    return value.text


def sheet_rows(zf: zipfile.ZipFile, path: str, strings: list[str], limit: int = 12) -> list[list[str]]:
    root = ET.fromstring(zf.read(path))
    data = root.find(f"{{{NS_MAIN}}}sheetData")
    rows: list[list[str]] = []
    if data is None:
        return rows
    for row in data.findall(f"{{{NS_MAIN}}}row"):
        values = [cell_value(cell, strings).strip() for cell in row.findall(f"{{{NS_MAIN}}}c")]
        if any(values):
            rows.append(values)
        if len(rows) >= limit:
            break
    return rows


def main() -> int:
    payload = fetch()
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        strings = shared_strings(zf)
        sheets = workbook_sheets(zf)
        probe = []
        for name, path in sheets:
            rows = sheet_rows(zf, path, strings)
            probe.append({"sheet": name, "path": path, "first_nonempty_rows": rows})
    print(json.dumps({
        "source": LANDING,
        "resource": URL,
        "license": "CC BY 4.0",
        "bytes": len(payload),
        "sheets": probe,
    }, ensure_ascii=False, indent=2))
    if not probe:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
