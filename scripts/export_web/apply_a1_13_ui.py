"""Apply the A1.13 robustness evidence card to an A1.12-capable site."""
from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.export_web.site_contract import (
    copy_docs,
    copy_web_assets,
    ensure_stylesheet,
    insert_before_recovery_card,
    merge_manifest_capabilities,
    read_json,
    require_paths,
    set_ui_stage,
)

CAPABILITIES = [
    "robustness-case-registry",
    "route-ranking-stability",
    "trip-ranking-stability",
    "equity-direction-stability",
    "robustness-boundary-conditions",
    "no-composite-robustness-score",
]


def _rank(value) -> str:
    return "—" if value is None else f"#{int(value)}"


def _case_label(case_by_id: dict[str, dict], case_id: str) -> str:
    item = case_by_id.get(case_id) or {}
    return str(item.get("label") or case_id)


def _changed_cases(case_by_id: dict[str, dict], case_ids: list[str]) -> str:
    if not case_ids:
        return "なし"
    return " / ".join(escape(_case_label(case_by_id, case_id)) for case_id in case_ids)


def _card(robustness: dict, cases_payload: dict) -> str:
    registry = cases_payload["case_registry"]
    case_by_id = {str(item["id"]): item for item in registry}
    route = robustness["route_stability"]
    trip = robustness["trip_stability"]
    boundaries = robustness["boundary_conditions"]

    route_case = {item["case_id"]: item for item in route["per_case"]}
    trip_case = {item["case_id"]: item for item in trip["per_case"]}
    rank_rows = []
    for case in registry:
        case_id = str(case["id"])
        route_item = route_case[case_id]
        trip_item = trip_case[case_id]
        rank_rows.append(
            "<tr>"
            f"<td><strong>{escape(str(case['label']))}</strong></td>"
            f"<td>{float(case['walk_speed_kmh']):.1f} km/h</td>"
            f"<td>{float(case['max_access_walk_minutes']):.0f}分</td>"
            f"<td>{float(case['max_transfer_walk_minutes']):.0f}分</td>"
            f"<td>{_rank(route_item['rank'])}</td>"
            f"<td>{escape(str(route_item.get('peak_departure_time') or '—'))}</td>"
            f"<td>{_rank(trip_item['rank'])}</td>"
            f"<td>{escape(str(trip_item.get('peak_departure_time') or '—'))}</td>"
            "</tr>"
        )

    equity_rows = []
    stability = robustness["equity_direction_stability"]
    destination_labels = {
        "hospital": "病院",
        "emergency": "指定緊急避難場所",
        "general": "指定一般避難所",
        "welfare": "指定福祉避難所",
    }
    group_labels = {"65plus": "65+", "75plus": "75+", "85plus": "85+"}
    for destination in ("hospital", "emergency", "general", "welfare"):
        for group in ("65plus", "75plus", "85plus"):
            affected = stability[destination][group]["affected_share_gt1min_gap_pp"]
            mean_gap = stability[destination][group]["mean_minutes_change_gap"]
            equity_rows.append(
                "<tr>"
                f"<td>{destination_labels[destination]}</td>"
                f"<td>{group_labels[group]}</td>"
                f"<td>{escape(str(affected['reference_direction']))}</td>"
                f"<td>{affected['same_direction_count']}/{affected['case_count']}</td>"
                f"<td>{_changed_cases(case_by_id, affected['changed_direction_cases'])}</td>"
                f"<td>{escape(str(mean_gap['reference_direction']))}</td>"
                f"<td>{mean_gap['same_direction_count']}/{mean_gap['case_count']}</td>"
                f"<td>{_changed_cases(case_by_id, mean_gap['changed_direction_cases'])}</td>"
                "</tr>"
            )

    boundary_ids = boundaries["case_ids"]
    if boundary_ids:
        boundary_html = "".join(
            f'<span class="robustness-boundary">{escape(_case_label(case_by_id, case_id))}</span>'
            for case_id in boundary_ids
        )
    else:
        boundary_html = '<span class="robustness-boundary stable">事前定義7条件で主要結論の境界変化なし</span>'

    return f'''<article class="analytics-card robustness-card" id="robustness-card">
      <div class="card-heading"><div><p class="pane-kicker">ROBUSTNESS / UNCERTAINTY</p><h2>結論は仮定を変えても残るか</h2></div><span class="classification classification-c">Accessibility C × Sensitivity assumptions D</span></div>
      <div class="robustness-kpis">
        <div class="robustness-kpi"><span>事前定義条件</span><strong>{robustness['case_count']}条件</strong><small>{robustness['slots_per_case']}時間帯 × 全条件</small></div>
        <div class="robustness-kpi"><span>基準Critical Route / Top 1維持</span><strong>{route['top1_count']}/{route['case_count']}</strong><small>{escape(str(route['reference_id']))} / Top 3 {route['top3_count']}/{route['case_count']}</small></div>
        <div class="robustness-kpi"><span>基準Critical Trip / Top 1維持</span><strong>{trip['top1_count']}/{trip['case_count']}</strong><small>Top 3 {trip['top3_count']}/{trip['case_count']}</small></div>
        <div class="robustness-kpi"><span>A1.12 baseline equivalence</span><strong>{escape(str(robustness['baseline_equivalence']['status']))}</strong><small>Goldenは別Gateで固定</small></div>
      </div>
      <h3 class="robustness-section-title">Critical Route / Trip の条件別順位</h3>
      <div class="robustness-table-scroll"><table class="robustness-table">
        <thead><tr><th>条件</th><th>歩行速度</th><th>Access上限</th><th>Transfer上限</th><th>Route順位</th><th>Route peak</th><th>Trip順位</th><th>Trip peak</th></tr></thead>
        <tbody>{''.join(rank_rows)}</tbody>
      </table></div>
      <h3 class="robustness-section-title">Equity gap の方向維持</h3>
      <div class="robustness-table-scroll"><table class="robustness-table">
        <thead><tr><th>目的地</th><th>年齢層</th><th>&gt;1分悪化率差 基準方向</th><th>維持</th><th>方向変化条件</th><th>平均時間差 基準方向</th><th>維持</th><th>方向変化条件</th></tr></thead>
        <tbody>{''.join(equity_rows)}</tbody>
      </table></div>
      <h3 class="robustness-section-title">境界条件</h3>
      <div class="robustness-boundaries">{boundary_html}</div>
      <p class="robustness-note">これは確率や信頼区間ではありません。歩行速度・アクセス徒歩上限・乗換徒歩上限の7つの事前定義条件をすべて同じコードパスで再計算し、基準結論が何条件で維持されたかをそのまま示しています。年齢層と目的地は都合よく選ぶパラメータではなく、全区分を評価しています。単一のRobustness Scoreは作成していません。</p>
    </article>'''


def apply(site: Path) -> dict:
    data = site / "data"
    require_paths(
        "A1.13 UI",
        [
            site / "index.html",
            site / "app.js",
            data / "summary.json",
            data / "manifest.json",
            data / "robustness_summary.json",
            data / "robustness_cases.json",
        ],
    )
    summary = read_json(data / "summary.json")
    robustness = read_json(data / "robustness_summary.json")
    cases_payload = read_json(data / "robustness_cases.json")
    manifest_path = data / "manifest.json"
    manifest = read_json(manifest_path)
    if summary.get("stage") != "A1.13" or robustness.get("stage") != "A1.13":
        raise ValueError("A1.13 analysis contract missing")
    if cases_payload.get("stage") != "A1.13" or len(cases_payload.get("case_registry") or []) != 7:
        raise ValueError("A1.13 sensitivity case registry invalid")
    if manifest.get("result_stage") != "A1.13" or manifest.get("ui_release_stage") != "A1.12":
        raise ValueError("A1.13 requires completed A1.12 predecessor UI")
    if robustness.get("composite_score") is not False:
        raise ValueError("A1.13 must not expose a composite robustness score")

    copy_web_assets(site, ("a1_13.css",))
    index_path = site / "index.html"
    html = index_path.read_text(encoding="utf-8")
    html = ensure_stylesheet(html, "a1_13.css")
    html = set_ui_stage(html, "A1.13")
    html = insert_before_recovery_card(
        html,
        _card(robustness, cases_payload),
        identity_marker='id="robustness-card"',
    )
    index_path.write_text(html, encoding="utf-8")

    merge_manifest_capabilities(
        manifest_path,
        result_stage="A1.13",
        ui_release_stage="A1.13",
        capabilities=CAPABILITIES,
    )
    copy_docs(site, ("A1_13_ROBUSTNESS_UNCERTAINTY.md",))

    result = {
        "result_stage": "A1.13",
        "ui_release_stage": "A1.13",
        "case_count": robustness["case_count"],
        "boundary_case_ids": robustness["boundary_conditions"]["case_ids"],
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
