# A1.12 — Vulnerable Population / Equity Analysis

## Purpose

A1.12は、A1.11までに計算済みの08:00 Accessibilityを年齢層別に再集計し、公共交通停止の負担が高齢者層で相対的に大きいかを透明な指標で確認するStageである。

## Population groups

- all: 全人口
- 65plus: 65歳以上
- 75plus: 75歳以上
- 85plus: 85歳以上

年齢層を「要配慮者」そのものとは扱わない。障害、医療的ケア、要介護認定等は含まれていない。

## Spatial population method

既存の「令和2年簡易100mメッシュ人口データ」には `Pop65over`, `Pop75over`, `Pop85over` が直接含まれている。A1.12はこれらをB区分の100m人口重みとして直接利用する。

大洲市の2026-07-31地域・年齢別人口はA区分・CC BY 4.0の最新公式統計として取得するが、地域集計を2020年100mメッシュへ按分しない。異なる時点・空間単位のデータを混ぜて偽の100m精度を作らないためである。

## Destinations

08:00のBaseline / 右回り停止について以下を評価する。

- 病院
- 指定緊急避難場所
- 指定一般避難所
- 指定福祉避難所

## Metrics

各年齢層について以下を独立に算出する。

- 分析範囲内人口
- Baseline 30分圏人口
- Baseline 60分圏人口
- 1分超 / 5分超 / 10分超悪化人口
- 1分超 / 5分超 / 10分超悪化率
- 人口加重平均所要時間 Baseline / 停止後 / 差

Equity gapは年齢層の値から全人口の値を引いた単純差である。

- `affected_share_gt1min_gap_pp`: percentage point差
- `mean_minutes_change_gap`: 分差

合成Vulnerability score、重み付き総合ランキング、規範的優先度スコアは作成しない。

## Provenance

- 大洲市GTFS等の既存A1入力: predecessor contractsを継承
- 2020簡易100m年齢人口: B
- 大洲市2026-07-31地域・年齢別人口: A / CC BY 4.0 / current context only
- Accessibility / Equity再集計: C
- 右回り停止: D stress-test

## Outputs

- `summary.json`
- `equity_summary.json`
- `vulnerable_population_access.geojson`
- A1.11までの全predecessor outputs

公開GeoJSONには100m年齢人口推計と計算済みAccessibility値を含める。大洲市2026年地域人口のraw ZIP/CSV/XLSXはPages artifactへ同梱しない。
