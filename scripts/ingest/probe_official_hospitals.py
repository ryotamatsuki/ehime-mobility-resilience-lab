"""Compact schema probe for Ehime's official medical-information workbook.

The workbook is downloaded transiently.  The probe prints only schema/count
metadata: it must not echo facility rows, names, addresses or coordinates into
GitHub Actions logs.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from accessibility.official_facilities import workbook_records

URL = "https://www.pref.ehime.jp/uploaded/attachment/188120.xlsx"
LANDING = "https://www.pref.ehime.jp/page/50405.html"
REQUIRED = {
    "機関コード",
    "機関区分",
    "活動区分",
    "正式名称",
    "略称",
    "所在地座標（緯度）",
    "所在地座標（経度）",
}


def fetch() -> bytes:
    request = urllib.request.Request(
        URL,
        headers={"User-Agent": "EhimeMobilityResilienceLab/0.1 (+GitHub Actions)"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def main() -> None:
    payload = fetch()
    records = workbook_records(payload)
    if not records:
        raise SystemExit("official medical workbook has no records")
    columns = set(records[0])
    missing = sorted(REQUIRED - columns)
    if missing:
        raise SystemExit("official medical workbook missing required columns: " + ", ".join(missing))
    active_hospitals = [
        row for row in records if row.get("機関区分") == "1" and row.get("活動区分") == "活動中"
    ]
    with_coordinates = [
        row
        for row in active_hospitals
        if row.get("所在地座標（緯度）") and row.get("所在地座標（経度）")
    ]
    print(
        json.dumps(
            {
                "landing": LANDING,
                "download_ok": True,
                "bytes": len(payload),
                "records": len(records),
                "active_hospitals": len(active_hospitals),
                "active_hospitals_with_coordinates": len(with_coordinates),
                "required_schema_ok": True,
                "raw_rows_logged": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
