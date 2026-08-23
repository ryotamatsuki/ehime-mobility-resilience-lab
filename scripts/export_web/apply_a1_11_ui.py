"""Apply the A1.11 time-dependent criticality UI capability."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.export_web.site_contract import (
    copy_docs,
    copy_web_assets,
    ensure_script,
    ensure_stylesheet,
    insert_before_recovery_card,
    merge_manifest_capabilities,
    read_json,
    require_paths,
    set_ui_stage,
)

ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_RESULT_STAGES = {"A1.11", "A1.12"}
CAPABILITIES = [
    "time-dependent-route-criticality",
    "time-dependent-trip-criticality",
    "hourly-criticality-matrix",
    "criticality-peak-time",
]


def apply(site: Path) -> dict:
    data = site / "data"
    require_paths(
        "A1.11 UI",
        [
            site / "index.html",
            site / "app.js",
            data / "summary.json",
            data / "manifest.json",
            data / "time_dependent_criticality.json",
        ],
    )

    summary = read_json(data / "summary.json")
    payload = read_json(data / "time_dependent_criticality.json")
    manifest_path = data / "manifest.json"
    manifest = read_json(manifest_path)
    result_stage = summary.get("stage")
    if result_stage not in SUPPORTED_RESULT_STAGES or payload.get("stage") != "A1.11":
        raise ValueError("A1.11 analysis contract missing")
    if manifest.get("result_stage") != result_stage or manifest.get("ui_release_stage") != "A1.10":
        raise ValueError("A1.11 requires A1.10 UI while preserving the real result stage")
    if len(payload.get("rows") or []) != 16:
        raise ValueError("A1.11 requires 16 hourly slots")

    copy_web_assets(site, ("a1_11.css", "a1_11_runtime.js"))
    index_path = site / "index.html"
    html = index_path.read_text(encoding="utf-8")
    html = ensure_stylesheet(html, "a1_11.css")
    html = ensure_script(html, "a1_11_runtime.js")
    html = set_ui_stage(html, "A1.11")

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
    html = insert_before_recovery_card(html, card, identity_marker='id="time-criticality-card"')
    index_path.write_text(html, encoding="utf-8")

    merge_manifest_capabilities(
        manifest_path,
        result_stage=result_stage,
        ui_release_stage="A1.11",
        capabilities=CAPABILITIES,
    )
    copy_docs(site, ("A1_11_TIME_DEPENDENT_CRITICALITY.md", "A1_11_QA_REPORT.md"))

    result = {
        "result_stage": result_stage,
        "ui_release_stage": "A1.11",
        "slots": len(payload["rows"]),
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