"""Probe the latest Ozu region/age population open data without publishing rows."""
from __future__ import annotations

import csv
import io
import json
import urllib.request
import zipfile

AGE_POP_URL = "https://www.city.ozu.ehime.jp/uploaded/attachment/48246.zip"
AGE_POP_LANDING = "https://www.city.ozu.ehime.jp/site/opendata/41647.html"
AGE_POP_AS_OF = "2026-07-31"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ehime-mobility-resilience-lab/0.1"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def decode_csv(payload: bytes) -> tuple[str, list[list[str]]]:
    for encoding in ("utf-8-sig", "cp932", "shift_jis"):
        try:
            text = payload.decode(encoding)
            rows = list(csv.reader(io.StringIO(text)))
            return encoding, rows
        except UnicodeDecodeError:
            continue
    raise ValueError("unable to decode CSV")


def main() -> int:
    payload = fetch(AGE_POP_URL)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = archive.namelist()
        csv_names = [name for name in names if name.lower().endswith(".csv")]
        if not csv_names:
            raise ValueError("Ozu age population ZIP contains no CSV")
        schema = []
        for name in csv_names:
            encoding, rows = decode_csv(archive.read(name))
            nonempty = [row for row in rows if any(str(cell).strip() for cell in row)]
            widths = sorted({len(row) for row in nonempty})
            preview = [[str(cell).strip() for cell in row[:12]] for row in nonempty[:6]]
            schema.append({
                "file": name,
                "encoding": encoding,
                "rows": len(nonempty),
                "widths": widths,
                "preview_first_6_rows_first_12_cells": preview,
            })
    print(json.dumps({
        "source": AGE_POP_LANDING,
        "as_of": AGE_POP_AS_OF,
        "license": "CC BY 4.0",
        "zip_bytes": len(payload),
        "files": names,
        "csv_schema": schema,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
