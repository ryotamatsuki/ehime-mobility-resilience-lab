# A1.10 QA Report — Destination Switcher

判定: **PASS WITH WARNINGS — mainへmerge可（最終head CI再通過を条件とする）**

## Release Gate

A1.10は次をRelease Gateとした。

1. A1.9実データ生成が回帰せずPASSする。
2. A1.10適用前のgenerated A1.9 siteが既存smoke testをPASSする。
3. A1.10 postprocessorがA1.9分析stageを変更しない。
4. A1.10適用後のgenerated siteが専用smoke testをPASSする。
5. 病院・指定緊急避難場所・指定一般避難所・指定福祉避難所の4destinationが利用可能である。
6. destination point countがA1.9のusable destination countと一致する。
7. shelter人口メッシュが全1840 zoneについて3destinationのBaseline / Scenario A / delta fieldを保持する。
8. browser側に新規routing/geocoderを導入しない。
9. `parent_feature`位置を厳密な運動場・入口座標として表示しない。
10. desktop/mobile CSS契約で48px以上のdestination touch targetを確保する。
11. manifestは `result_stage: A1.9` のまま、`ui_release_stage: A1.10` とする。
12. Pages artifactにRaw公式Excelを含めない。

PR-triggered real-data CI run `32598137380` で上記GateをすべてPASSした。

## Source contract

確認対象:

- `web/app.js`
- `web/a1_10.css`
- `web/a1_10_runtime.js`
- `scripts/export_web/apply_a1_10_ui.py`
- `web/tests/a1_10_smoke.js`

A1.10はA1.9の公開成果物を表示するUI層であり、Python分析モデルは変更しない。

Source CIで次をPASSした。

- `node --check web/app.js`
- `node --check web/a1_10_runtime.js`
- A1.9-compatible source smoke
- A1.10 source smoke
- client-side routing/geocoder禁止契約
- desktop/mobile CSS契約

最初のPR CI run `32598105535` では、runtimeがDOM API `dataset.uiStage` を用いていたのにsource smokeが文字列 `data-ui-stage` を直接要求していたため、テスト契約のmarker不一致で `web_source` が失敗した。実装JSのsyntax errorではない。テストとruntime契約を整合させた後、run `32598137380` でPASSした。

## Real-data regression result

run `32598137380` でA1.9を公式データ・OSMから再生成した結果、前回確定値と一致した。

### Destination counts

- 病院: 5
- 指定緊急避難場所: 4
- 指定一般避難所: 13
- 指定福祉避難所: 2
- 避難所合計: 19

避難所の位置品質:

- 指定緊急避難場所: `exact` 2 / `parent_feature` 2
- 指定一般避難所: `name_equivalent` 13
- 指定福祉避難所: `name_equivalent` 2

曖昧一致は一般避難所1件・福祉避難所1件で、A1.9と同様にAccessibility対象から除外された。

注意: 市全体の公式件数60 / 96 / 20は分析範囲内施設数ではないため、4/60等を分析範囲内の照合率として扱わない。

### A1.9 Accessibility regression

08:00 / 右回り route 11・21運休Stress Test:

| Destination | 使用施設 | Baseline 30分圏 | Scenario A 30分圏 | 1分超悪化人口 | 平均悪化 |
|---|---:|---:|---:|---:|---:|
| 指定緊急避難場所 | 4 | 20,789.8079 | 20,381.2975 | 1,035.1204 | +0.201分 |
| 指定一般避難所 | 13 | 25,055.4109 | 25,053.2837 | 1,375.3316 | +0.230分 |
| 指定福祉避難所 | 2 | 15,090.5726 | 15,064.1391 | 981.8614 | +0.230分 |

A1.8 regressionも同runで維持された。

- route ranking: 4路線
- trip ranking: 11便
- Top route / trip: route 21
- route 21停止時の1分超悪化人口: 1,955.2890人相当
- 平均所要時間悪化: +0.728分

## Ordered generated-site Gate

CIでは要求順序を明示的に分離した。

### Gate 1 — generated A1.9 site

`build_a1_2_demo.py` でA1.9成果物から `_site` を生成。

確認値:

- GTFS stops: 37
- population zones: 1,840
- hospital destinations: 5
- walking transfer edges: 156
- temporal slots: 16
- routes ranked: 4
- trips ranked: 11
- shelter destinations: 19

A1.10適用前にA1.9-compatible smokeを実施しPASS。

- `result_stage == A1.9`
- `ui_release_stage` 未設定
- `shelter-map-layer` capability未設定

これによりA1.9がA1.10を先取りして虚偽advertiseしていないことを確認した。

### Gate 2 — A1.10 apply

`apply_a1_10_ui.py` を実行し、分析値を変更せず次を追加した。

- `ui_release_stage: A1.10`
- `destination-switcher`
- `shelter-map-layer`
- `destination-synchronized-metrics`
- `destination-synchronized-charts`
- `destination-provenance-popups`

postprocessor出力で4destinationを確認した。

- hospital: 5
- emergency: 4
- general: 13
- welfare: 2

### Gate 3 — generated A1.10 site

A1.10適用後に専用smokeを実行しPASS。

確認内容:

- `node --check _site/app.js`
- `node --check _site/a1_10_runtime.js`
- `a1_10.css` / `a1_10_runtime.js` がHTMLから参照される
- body `data-ui-stage="A1.10"`
- `result_stage == A1.9`
- `ui_release_stage == A1.10`
- destination public point countとA1.9 usable countが一致
- 全1,840メッシュに3種避難所のBaseline / Scenario A / delta fieldが存在
- `parent_feature` warningが実装されている
- Raw公式Excelが公開bundleに存在しない

## UI truthfulness contract

- 病院popup: 愛媛県公式台帳で現行性確認済み、公開位置・名称はOSM由来。
- 避難所popup: 大洲市公式属性A + OSM位置B。
- `parent_feature`: 「親施設のOSM代表位置」と表示する。
- 収容人数は表示可能だが、A1.10では容量制約として使わない。
- 災害時の開設可否・実被害・混雑を予測したと表示しない。
- ブラウザ側でルーティング・ジオコーディング・Accessibility再計算をしない。

## CSS / accessibility contract

PASS確認:

- radio groupとして操作可能
- desktop: 2列
- <=900px: 2列
- <=420px: 1列
- min touch target: 48px
- focus-visible outlineあり
- selected destinationは視覚的に区別
- destination変更時にmap aria-labelを同期
- destination別に凡例色を同期

## Artifact

PR CI run `32598137380`:

- artifact: `a1-10-planning-canvas`
- artifact ID: `9482131138`
- size: 327,265 bytes
- SHA-256: `c7ba6549a4a347236ab80170a322d5e9a6b08d75ece0738e82ae58ffb5b72093`

Artifact uploadはPASSした。PR runのためPages configure/upload/deploy stepは条件どおりskipされた。

## Regression / CI summary

run `32598137380` で次がPASSした。

- Python unit tests
- A0 foundation checks
- public data contract validation
- deterministic model fixture
- Python compile
- A1 source probe
- 愛媛県公式医療機関台帳probe
- 大洲市公式避難所Excel probe
- A1.9実データ再生成
- A1.5公式病院Gate regression
- A1.6 walking transfer regression
- A1.7 temporal resilience regression
- A1.8 route/trip criticality regression
- A1.9 result contract
- generated A1.9 site smoke
- A1.10 postprocess
- generated A1.10 site smoke
- artifact upload

## Warnings

1. 分析範囲は大洲市全域ではなく、ぐるりんおおずGTFS停留所bbox周辺である。
2. 大洲市公式避難所Excelに座標がないため、OSMで一意照合できたsubsetのみを表示・計算している。
3. `parent_feature`は親施設の代表位置であり、運動場・入口等の厳密位置ではない。
4. OSM/Overpassはlive外部依存であり、将来の正当なOSM更新により照合件数は変化し得る。このためCIは固定件数ではなく、summaryと公開GeoJSONの整合性・各種1件以上をRelease Gateとする。
5. 人口は令和2年簡易100mメッシュの按分値であり実測100m人口ではない。
6. 避難所収容人数は容量制約・混雑配分に使用していない。
7. A1.10はStress Test UIであり実災害時の被害・施設開設状況を予測しない。
8. GTFSに`shapes.txt`がないため、路線表示形状には停留所順polyline fallbackが含まれる。
9. OSM標準tileはPoC規模利用を前提とする。
10. 複数ブラウザ・実端末によるpixel-level visual regressionは本Gateでは実施していない。source/generated DOM・CSS・JS契約smokeをRelease Gateとした。

以上から、A1.10は **PASS WITH WARNINGS** とする。QA文書更新後の最終headでも同一CIを再実行し、全Gate PASSを確認してからReady for review → squash mergeする。
