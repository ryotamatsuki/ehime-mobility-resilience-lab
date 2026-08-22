"""Apply A1.11 time-dependent criticality UI to an A1.10-compatible site."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPABILITIES = [
    "time-dependent-route-criticality",
    "time-dependent-trip-criticality",
    "hourly-criticality-matrix",
    "criticality-peak-time",
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def apply(site: Path) -> dict:
    data = site / "data"
    required = [site / "index.html", site / "app.js", data / "summary.json", data / "manifest.json", data / "time_dependent_criticality.json"]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("A1.11 UI requires: " + ", ".join(missing))

    summary = read_json(data / "summary.json")
    payload = read_json(data / "time_dependent_criticality.json")
    manifest_path = data / "manifest.json"
    manifest = read_json(manifest_path)
    if summary.get("stage") != "A1.11" or payload.get("stage") != "A1.11":
        raise ValueError("A1.11 analysis contract missing")
    if manifest.get("result_stage") != "A1.11" or manifest.get("ui_release_stage") != "A1.10":
        raise ValueError("A1.11 requires the A1.10 predecessor UI and A1.11 result stage")
    if len(payload.get("rows") or []) != 16:
        raise ValueError("A1.11 requires 16 hourly slots")

    for asset in ("a1_11.css", "a1_11_runtime.js"):
        shutil.copy2(ROOT / "web" / asset, site / asset)

    index_path = site / "index.html"
    html = index_path.read_text(encoding="utf-8")
    if 'href="a1_11.css"' not in html:
        html = html.replace('</head>', '  <link rel="stylesheet" href="a1_11.css">\n</head>', 1)
    if 'src="a1_11_runtime.js"' not in html:
        html = html.replace('</body>', '  <script src="a1_11_runtime.js"></script>\n</body>', 1)
    html = html.replace('data-ui-stage="A1.10"', 'data-ui-stage="A1.11"', 1)

    card = '''<article class="analytics-card time-criticality-card" id="time-criticality-card">
      <div class="card-heading"><div><p class="pane-kicker">TIME × SERVICE CRITICALITY</p><h2>時間帯別 Route / Trip Criticality</h2></div><span class="classification classification-c">病院アクセス / C推計・D停止仮定</span></div>
      <div class="time-criticality-kpis">
        <div class="time-criticality-kpi"><span>Route最大影響</span><div id="time-criticality-peak-route"><strong>読み込み中</strong></div></div>
        <div class="time-criticality-kpi"><span>Trip最大影響</span><div id="time-criticality-peak-trip"><strong>読み込み中</strong></div></div>
        <div class="time-criticality-kpi"><span>最重要サービスの入替</span><div id="time-criticality-changes"><strong>読み込み中</strong></div></div>
      </div>
      <div class="time-criticality-scroll"><table class="time-criticality-table">
        <thead><tr><th>時刻</th><th>最重要Route</th><th>Route影響</th><th>最重要Trip</th><th>Trip影響</th><th>残存Trip</th></tr></thead>
        <tbody id="time-criticality-body"><tr><td colspan="6">A1.11を読み込み中...</td></tr></tbody>
      </table></div>
      <p class="time-criticality-note">各時刻でroute/tripを1件ずつ停止するleave-one-out感度分析。順位は1分超悪化人口→平均時間悪化。病院アクセスのみを評価し、故障確率・利用者数・運行重要度そのものを示す指標ではありません。</p>
    </article>'''
    marker = '<article class="analytics-card recovery-card">'
    if "time-criticality-card" not in html:
        if marker not in html:
            raise ValueError("A1.11 insertion marker missing")
        html = html.replace(marker, card + marker, 1)
    index_path.write_text(html, encoding="utf-8")

    app_path = site / "app.js"
    app = app_path.read_text(encoding="utf-8")
    old = '["A1.1","A1.5","A1.6","A1.7","A1.8","A1.9"]'
    new = '["A1.1","A1.5","A1.6","A1.7","A1.8","A1.9","A1.11"]'
    if old in app:
        app = app.replace(old, new)
    elif '"A1.11"' not in app:
        raise ValueError("A1.11 app stage contract patch target missing")
    app_path.write_text(app, encoding="utf-8")

    manifest["ui_release_stage"] = "A1.11"
    capabilities = list(manifest.get("ui_capabilities") or [])
    for capability in CAPABILITIES:
        if capability not in capabilities:
            capabilities.append(capability)
    manifest["ui_capabilities"] = capabilities
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    docs_out = site / "docs"
    docs_out.mkdir(exist_ok=True)
    for name in ("A1_11_TIME_DEPENDENT_CRITICALITY.md", "A1_11_QA_REPORT.md"):
        src = ROOT / "docs" / name
        if src.exists():
            shutil.copy2(src, docs_out / name)

    result = {"result_stage": "A1.11", "ui_release_stage": "A1.11", "slots": len(payload["rows"]), "capabilities_added": CAPABILITIES}
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
