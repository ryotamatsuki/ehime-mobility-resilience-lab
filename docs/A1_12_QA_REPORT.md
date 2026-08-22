# A1.12 QA Report — Vulnerable Population / Equity Analysis

判定: **PASS WITH WARNINGS — mainへのmerge可**

## Release Gate

1. A1.11 predecessor outputsを回帰なく再生成 — PASS。
2. 100mソースの `Pop65over`, `Pop75over`, `Pop85over` を直接利用 — PASS。
3. 全1840 analysis zonesで `0 <= 85+ <= 75+ <= 65+ <= 全人口` — PASS。
4. 大洲市2026-07-31地域・年齢別人口をA / CC BY 4.0のcurrent contextとして取得 — PASS。
5. 2026地域人口を100mへ空間按分しない — PASS。
6. hospital / emergency / general / welfare × all / 65+ / 75+ / 85+ を計算 — PASS。
7. 1分超悪化率が0〜100% — PASS。
8. Equity gapはpercentage point / 分の単純差のみ。合成scoreなし — PASS。
9. `vulnerable_population_access.geojson` は1840 featuresで分析zone数と一致 — PASS。
10. A1.10 Destination SwitcherとA1.11 Time-dependent Criticalityを回帰保持 — PASS。
11. Planning Canvas A1.12 Equityカード生成 — PASS。
12. client-side routing/geocoding追加なし — PASS。
13. raw age-population ZIP/CSV/XLSX、公式医療・避難所workbookをPages artifactへ含めない — PASS。
14. Python/source/predecessor/generated-site smoke — PASS。

## Verified CI

Workflow run: `32605041213`

- `python`: success
- `web_source`: success
- `a1_source_probe`: success
- `a1_real_accessibility`: success
- A1.11 predecessor regression smoke: success
- generated A1.12 smoke: success
- artifact upload: success

実データbuild開始からartifact確定までは概ね23:23:05〜23:25:26で、A1.11 predecessor再生成を含め約2分21秒だった。

## Population data

### 2020 simplified 100 m mesh — analysis envelope / B

A1.12は元データに既に存在する年齢項目を直接利用し、新しい空間按分をしていない。

- 全人口: **26,553.4167人相当**
- 65歳以上: **8,231.8731人相当**
- 75歳以上: **4,197.0790人相当**
- 85歳以上: **1,606.2811人相当**

### Ozu official region-age population — current context / A

時点: **2026-07-31**、CC BY 4.0。

- 地域行: 40
- 総人口: **37,725人**
- 65歳以上: **14,868人 / 39.412%**
- 75歳以上: **8,700人 / 23.062%**
- 85歳以上: **3,247人 / 8.607%**

この2026年値はcurrent city contextに限定し、2020年100mメッシュへ上書き・按分していない。

## Hospital equity — 08:00 right-loop outage

| Group | >1min affected | Share | Mean change | Share gap vs all | Mean gap vs all |
|---|---:|---:|---:|---:|---:|
| All | 2,030.3675 | 7.646% | +0.732 min | — | — |
| 65+ | 639.3862 | 7.767% | +0.793 min | +0.121 pp | +0.061 min |
| 75+ | 353.2373 | 8.416% | +0.887 min | +0.770 pp | +0.155 min |
| 85+ | 143.1335 | 8.911% | +0.988 min | +1.265 pp | +0.256 min |

病院アクセスでは年齢層が上がるほど、今回の100m人口分布上では1分超悪化率と平均悪化時間が大きくなる傾向が確認された。ただしこれは記述的なモデル結果であり、年齢そのものの因果効果ではない。

## Welfare shelter equity — 08:00 right-loop outage

| Group | >1min affected | Share | Mean change | Share gap vs all | Mean gap vs all |
|---|---:|---:|---:|---:|---:|
| All | 981.8614 | 3.698% | +0.230 min | — | — |
| 65+ | 367.6598 | 4.466% | +0.247 min | +0.768 pp | +0.017 min |
| 75+ | 184.0505 | 4.385% | +0.257 min | +0.687 pp | +0.027 min |
| 85+ | 70.4401 | 4.385% | +0.302 min | +0.687 pp | +0.072 min |

指定緊急避難場所・指定一般避難所についても同じ4人口群・同じtransparent metricsで計算し、`equity_summary.json` に保存済み。

## Artifact

- name: `a1-12-planning-canvas`
- artifact ID: `9483931435`
- size: 590,823 bytes
- SHA-256: `ad8bf429fb3d865db009899965c49c0ad43edcc4ee820c8d58b5c384179cf00f`

## Truthfulness

- 100m年齢人口は2020年簡易メッシュ推計（B）。
- 2026-07-31地域・年齢別人口は大洲市公式統計（A）だがcurrent context専用。
- 65+/75+/85+を全要配慮者と同一視しない。
- AccessibilityとEquity再集計はC。
- 右回り停止はD stress-test。
- Equity gapは負担差の記述指標で、因果効果・政策優先順位ではない。
- 合成Vulnerability scoreは生成しない。

## Warnings

1. 100m年齢人口の空間分布は2020年ベースで、2026年公式人口との時点差がある。
2. 100m人口は簡易配分データで小数の「人相当」であり、個人単位の実在地点を示さない。
3. 高齢者区分は要配慮人口の一部のproxyであり、障害、要介護、医療的ケア等を含まない。
4. Shelter側はA1.9でOSM位置を厳格照合できた分析範囲内subsetのみを対象とする。
5. Equity gapは人口分布とモデル経路の結果であり、年齢による因果効果や規範的な復旧優先度ではない。
6. OSMはlive外部データのため、将来更新により細かな値が変動しうる。
