"""Probe the official Ehime medical basic-information workbook without persisting it.

The workbook is published by Ehime Prefecture Medical Policy Division and is
used only to inspect schema/values for A1.5.  Raw bytes are not written to the
repository or uploaded as an artifact.
"""
from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from xml.etree import ElementTree as ET

URL = "https://www.pref.ehime.jp/uploaded/attachment/188120.xlsx"
LANDING = "https://www.pref.ehime.jp/page/50405.html"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
PKG = {"p": "http://schemas.openxmlformats.org/package/2006/relationships"}


def fetch() -> bytes:
    req = urllib.request.Request(URL, headers={"User-Agent": "EhimeMobilityResilienceLab/0.1 (+GitHub Actions)"})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()


def shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    out: list[str] = []
    for si in root.findall("m:si", NS):
        out.append("".join((t.text or "") for t in si.findall(".//m:t", NS)))
    return out


def sheet_targets(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("p:Relationship", PKG)}
    out = []
    for sheet in workbook.findall("m:sheets/m:sheet", NS):
        rid = sheet.attrib[f"{{{NS['r']}}}id"]
        target = relmap[rid].lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        out.append((sheet.attrib.get("name", rid), target))
    return out


def cell_value(cell: ET.Element, strings: list[str]) -> str:
    typ = cell.attrib.get("t")
    if typ == "inlineStr":
        return "".join((t.text or "") for t in cell.findall(".//m:t", NS))
    value = cell.findtext("m:v", default="", namespaces=NS)
    if typ == "s" and value:
        return strings[int(value)]
    return value


def rows(zf: zipfile.ZipFile, target: str, strings: list[str], limit: int = 25) -> list[list[str]]:
    root = ET.fromstring(zf.read(target))
    out: list[list[str]] = []
    for row in root.findall(".//m:sheetData/m:row", NS):
        vals = [cell_value(cell, strings).strip() for cell in row.findall("m:c", NS)]
        if any(vals):
            out.append(vals)
        if len(out) >= limit:
            break
    return out


def main() -> None:
    payload = fetch()
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        strings = shared_strings(zf)
        sheets = []
        for name, target in sheet_targets(zf):
            sample = rows(zf, target, strings)
            sheets.append({"name": name, "target": target, "sample_rows": sample})
    print(json.dumps({"landing": LANDING, "bytes": len(payload), "sheets": sheets}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
