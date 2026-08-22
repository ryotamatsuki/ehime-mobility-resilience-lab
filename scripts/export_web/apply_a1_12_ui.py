"""Apply A1.12 vulnerable-population/equity UI to an A1.11 site."""
from __future__ import annotations

import argparse
import json
import shutil
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPABILITIES = [
    "vulnerable-population-65plus",
    "vulnerable-population-75plus",
    "vulnerable-population-85plus",
    "equity-gap-metrics",
    "equity-public-geojson",
    "current-official-age-context",
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_number(value, digits=0) -> str:
    if value is None:
        return "—"
    return f"{float(value):,.{digits}f}"


def fmt_gap(value, suffix="pt") -> str:
    if value is None:
        return "—"
    number = float(value)
    return f"{number:+.3f}{suffix}"


def _card(equity: dict) -> str:
    sources = equity["population_sources"]
    mesh = sources["mesh_age_population"]["analysis_envelope"]
    current = sources["current_official_context"]
    destinations = equity["destinations"]
    h75 = destinations["hospital"]["gaps_vs_all"]["75plus"]["affected_share_gt1min_gap_pp"]
    w75 = destinations["welfare"]["gaps_vs_all"]["75plus"]["affected_share_gt1min_gap_pp"]

    rows = []
    for key in ("hospital", "emergency", "general", "welfare"):
        item = destinations[key]
        groups = item["groups"]
        gaps = item["gaps_vs_all"]
        rows.append(
            "<tr>"
            f"<td><strong>{escape(str(item['label']))}</strong></td>"
            f"<td>{fmt_number(groups['all']['affected_share_gt1min_pct'],3)}%</td>"
            f"<td>{fmt_number(groups['65plus']['affected_share_gt1min_pct'],3)}%</td>"
            f"<td>{fmt_number(groups['75plus']['affected_share_gt1min_pct'],3)}%</td>"
            f"<td>{fmt_number(groups['85plus']['affected_share_gt1min_pct'],3)}%</td>"
            f"<td>{fmt_gap(gaps['75plus']['affected_share_gt1min_gap_pp'])}</td>"
            f"<td>{fmt_gap(gaps['85plus']['affected_share_gt1min_gap_pp'])}</td>"
            f"<td>{fmt_gap(gaps['75plus']['mean_minutes_change_gap'],'分')}</td>"
            "</tr>"
        )

    return f'''<article class="analytics-card equity-card" id="equity-card">
      <div class="card-heading"><div><p class="pane-kicker">VULNERABLE POPULATION / EQUITY</p><h2>年齢層別 Accessibility 影響</h2></div><span class="classification classification-c">100m年齢人口 B × Accessibility C</span></div>
      <div class="equity-kpis">
        <div class="equity-kpi"><span>65歳以上 / 分析範囲</span><strong>{fmt_number(mesh['population_65plus'])}人相当</strong><small>2020簡易100mメッシュ B</small></div>
        <div class="equity-kpi"><span>75歳以上 / 分析範囲</span><strong>{fmt_number(mesh['population_75plus'])}人相当</strong><small>85歳以上 {fmt_number(mesh['population_85plus'])}人相当</small></div>
        <div class="equity-kpi"><span>病院 75+ 負担差</span><strong>{fmt_gap(h75)}</strong><small>&gt;1分悪化率 − 全人口</small></div>
        <div class="equity-kpi"><span>福祉避難所 75+ 負担差</span><strong>{fmt_gap(w75)}</strong><small>&gt;1分悪化率 − 全人口</small></div>
      </div>
      <div class="equity-table-scroll"><table class="equity-table">
        <thead><tr><th>目的地</th><th>全人口</th><th>65+</th><th>75+</th><th>85+</th><th>75+差</th><th>85+差</th><th>75+平均時間差</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table></div>
      <p class="equity-note">表は08:00右回り停止時の「1分超悪化人口の各年齢層内割合」。差は各年齢層 − 全人口のpercentage pointです。合成Vulnerability scoreは作成していません。100mの65+/75+/85+は元データに直接含まれる2020年簡易メッシュ推計（B）です。大洲市2026-07-31地域年齢人口（A、総人口 {fmt_number(current['population'])}人）は最新状況の文脈確認にのみ使用し、100mへ按分していません。</p>
    </article>'''


def apply(site: Path) -> dict:
    data = site / "data"
    required = [
        site / "index.html", site / "app.js", data / "summary.json", data / "manifest.json",
        data / "equity_summary.json", data / "vulnerable_population_access.geojson",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("A1.12 UI requires: " + ", ".join(missing))
    summary = read_json(data / "summary.json")
    equity = read_json(data / "equity_summary.json")
    manifest_path = data / "manifest.json"
    manifest = read_json(manifest_path)
    if summary.get("stage") != "A1.12" or equity.get("stage") != "A1.12":
        raise ValueError("A1.12 analysis contract missing")
    if manifest.get("result_stage") != "A1.12" or manifest.get("ui_release_stage") != "A1.11":
        raise ValueError("A1.12 requires A1.11 predecessor UI")

    shutil.copy2(ROOT / "web" / "a1_12.css", site / "a1_12.css")
    index_path = site / "index.html"
    html = index_path.read_text(encoding="utf-8")
    if 'href="a1_12.css"' not in html:
        html = html.replace('</head>', '  <link rel="stylesheet" href="a1_12.css">\n</head>', 1)
    html = html.replace('data-ui-stage="A1.11"', 'data-ui-stage="A1.12"', 1)
    card = _card(equity)
    marker = '<article class="analytics-card recovery-card">'
    if 'id="equity-card"' not in html:
        if marker not in html:
            raise ValueError("A1.12 insertion marker missing")
        html = html.replace(marker, card + marker, 1)
    index_path.write_text(html, encoding="utf-8")

    app_path = site / "app.js"
    app = app_path.read_text(encoding="utf-8")
    old = '["A1.1","A1.5","A1.6","A1.7","A1.8","A1.9","A1.11"]'
    new = '["A1.1","A1.5","A1.6","A1.7","A1.8","A1.9","A1.11","A1.12"]'
    if old in app:
        app = app.replace(old, new)
    elif '"A1.12"' not in app:
        raise ValueError("A1.12 app stage contract patch target missing")
    app_path.write_text(app, encoding="utf-8")

    manifest["ui_release_stage"] = "A1.12"
    capabilities = list(manifest.get("ui_capabilities") or [])
    for capability in CAPABILITIES:
        if capability not in capabilities:
            capabilities.append(capability)
    manifest["ui_capabilities"] = capabilities
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    docs_out = site / "docs"
    docs_out.mkdir(exist_ok=True)
    for name in ("A1_12_VULNERABLE_EQUITY.md", "A1_12_QA_REPORT.md"):
        src = ROOT / "docs" / name
        if src.exists():
            shutil.copy2(src, docs_out / name)

    result = {
        "result_stage": "A1.12", "ui_release_stage": "A1.12",
        "groups": [item["id"] for item in equity["groups"]],
        "destinations": list(equity["destinations"]),
        "capabilities_added": CAPABILITIES,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    apply(args.site)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
