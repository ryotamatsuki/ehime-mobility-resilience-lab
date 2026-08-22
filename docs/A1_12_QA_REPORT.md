# A1.12 QA Report — Vulnerable Population / Equity Analysis

判定: **PENDING — real-data CI待ち**

## Release Gate

1. A1.11 predecessor outputsを回帰なく再生成する。
2. 100mソースに `Pop65over`, `Pop75over`, `Pop85over` が存在する。
3. 全100m zoneで `0 <= 85+ <= 75+ <= 65+ <= 全人口` を満たす。
4. 大洲市2026-07-31地域・年齢別人口をA/CC BY 4.0のcurrent contextとして取得できる。
5. 2026地域人口を100mへ空間按分しない。
6. hospital / emergency / general / welfare の4目的地について all/65+/75+/85+ を計算する。
7. 1分超悪化率が0〜100%の範囲である。
8. Equity gapは単純なpercentage point / 分差のみとし、合成scoreを生成しない。
9. `vulnerable_population_access.geojson` 件数が分析人口zone数と一致する。
10. A1.10 Destination SwitcherとA1.11 Time-dependent Criticalityを維持する。
11. Planning CanvasにA1.12 Equityカードを表示する。
12. client-side routing/geocodingを追加しない。
13. raw age-population ZIP/CSV/XLSXをPages artifactへ含めない。
14. Python/source/predecessor/generated-site smokeをすべてPASSする。

## Truthfulness

- 100m年齢人口は2020年簡易メッシュ推計（B）。
- 2026-07-31地域・年齢別人口は大洲市公式統計（A）だがcurrent context専用。
- 65+/75+/85+を全要配慮者と同一視しない。
- AccessibilityとEquity再集計はC。
- 右回り停止はD stress-test。
- Equity gapは負担差の記述指標で、因果効果・政策優先順位ではない。

## CI Result

未確定。実データCI後に年齢人口、目的地別悪化率、Equity gap、artifactを記録する。
