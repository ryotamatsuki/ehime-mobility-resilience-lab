# A1.10 Destination Switcher

## 目的

A1.9で実計算済みの4種類のAccessibility destinationを、Planning Canvas上で同一の操作体系で切り替えて比較できるようにする。

対象:

- 病院
- 指定緊急避難場所
- 指定一般避難所
- 指定福祉避難所

A1.10はUI-only Stageである。経路探索、徒歩ネットワーク、GTFS時刻表探索、人口配分、避難所位置照合、Accessibility値は再計算しない。分析結果stageはA1.9のまま維持する。

## Single Source of Truth

A1.10が読む公開成果物:

- `summary.json`
- `population_access.geojson` — 病院Accessibility
- `facilities.geojson` — 病院位置
- `shelters.geojson` — A1.9で一意照合済みの避難所位置
- `shelter_accessibility.json`
- `shelter_population_access.geojson`

UIはこれらの値を表示するだけであり、ブラウザ内でルーティング・ジオコーディング・Accessibility再計算を行わない。

## UI契約

### 1. Destination selector

Scenario Builderに4択の目的地selectorを追加する。

- keyboard操作可能なradio group
- desktopは2列
- mobileは2列、420px以下は1列
- touch targetは48px以上
- 未計算destinationはdisabled

### 2. 地図同期

選択destinationに応じて次を同時に切り替える。

- destination point layer
- 100m人口メッシュの所要時間色
- Difference表示のdelta色
- popupのBaseline / Scenario A / 差分
- map scale title
- legend destination label/color

施設位置の色:

- 病院: purple
- 指定緊急避難場所: red
- 指定一般避難所: green
- 指定福祉避難所: purple-violet

### 3. 指標同期

右ペインは選択destinationのA1.9結果へ同期する。

- 1分超悪化人口
- +1 / +5 / +10分人口
- 60分以内到達人口
- 60分以内到達不能化人口
- 人口加重平均アクセス時間
- 影響地域ranking
- destination count

### 4. analytics同期

下段も同じdestinationへ同期する。

- Before
- Difference
- After
- population-weighted CDF
- Recovery benefit

## Provenance / truthfulness

### 病院

- 現行性Gate: 愛媛県公式医療機関台帳 A
- 公開位置・名称: OpenStreetMap B
- Accessibility: C
- 右回り運休: D

### 避難所

- 施設属性: 大洲市公式オープンデータ A
- 位置: A1.9で一意照合したOpenStreetMap B
- Accessibility: C
- 右回り運休: D

避難所popupは `location_match_quality` を必ず表示上考慮する。

- `exact`: 名称完全一致
- `name_equivalent`: 表記差を正規化した一意照合
- `parent_feature`: 親施設のOSM代表位置。運動場・入口等の厳密座標とは主張しない

## Generated-site architecture

A1.10はA1.9 regressionを保護するため、次の順に生成する。

1. `build_a1_9.py` でA1.9実データ成果物を生成
2. `build_a1_2_demo.py` で従来Planning Canvasを生成
3. A1.9-compatible smoke testを実行
4. `apply_a1_10_ui.py` を実行
5. `a1_10.css` / `a1_10_runtime.js` を有効化
6. manifestに `ui_release_stage: A1.10` を追加
7. A1.10 generated-site smoke testを実行
8. GitHub Pages artifactを生成

これにより、A1.9の分析契約とA1.10のUI契約を別々にQAできる。

## A1.10 manifest capabilities

- `destination-switcher`
- `shelter-map-layer`
- `destination-synchronized-metrics`
- `destination-synchronized-charts`
- `destination-provenance-popups`

A1.9では未実装だった `shelter-map-layer` は、A1.10で初めてtruthfulにadvertiseする。

## Scope外

- 避難所の容量制約付き割当
- 最寄り避難所の混雑・収容余力
- 災害種別ごとの緊急避難場所filter
- wheelchair / age / care-needs別の個人属性routing
- 実災害時の施設開設状況
- 新たな道路障害scenario

これらをA1.10の結果として表示してはならない。
