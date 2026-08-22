# A1.10 QA Report — Destination Switcher

判定: **PENDING — full real-data CI / generated-site smoke待ち**

## Release Gate

A1.10は次をすべて満たした場合のみmainへmergeする。

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

## Source contract

確認対象:

- `web/app.js`
- `web/a1_10.css`
- `web/a1_10_runtime.js`
- `scripts/export_web/apply_a1_10_ui.py`
- `web/tests/a1_10_smoke.js`

A1.10はA1.9の公開成果物を表示するUI層であり、Python分析モデルは変更しない。

## Expected destination counts

A1.9の確定値を回帰基準とする。

- 病院: 5
- 指定緊急避難場所: 4
- 指定一般避難所: 13
- 指定福祉避難所: 2

避難所合計: 19

## Expected A1.9 accessibility regression

08:00 / 右回り route 11・21運休Stress Test:

| Destination | 使用施設 | Baseline 30分圏 | Scenario A 30分圏 | 1分超悪化人口 | 平均悪化 |
|---|---:|---:|---:|---:|---:|
| 指定緊急避難場所 | 4 | 20,789.8079 | 20,381.2975 | 1,035.1204 | +0.201分 |
| 指定一般避難所 | 13 | 25,055.4109 | 25,053.2837 | 1,375.3316 | +0.230分 |
| 指定福祉避難所 | 2 | 15,090.5726 | 15,064.1391 | 981.8614 | +0.230分 |

A1.10はこれらの値を変更してはならない。

## UI truthfulness contract

- 病院popup: 愛媛県公式台帳で現行性確認済み、公開位置・名称はOSM由来。
- 避難所popup: 大洲市公式属性A + OSM位置B。
- `parent_feature`: 「親施設のOSM代表位置」と表示する。
- 収容人数は表示可能だが、A1.10では容量制約として使わない。
- 災害時の開設可否・実被害・混雑を予測したと表示しない。

## CSS / accessibility contract

- radio groupとして操作可能
- desktop: 2列
- <=900px: 2列
- <=420px: 1列
- min touch target: 48px
- focus-visible outlineあり
- selected destinationは視覚的に区別
- destination変更時にmap aria-labelを同期

## CI result

未実行。最終headのworkflow run、artifact、generated-site smoke結果をここへ追記後にRelease Gate判定を更新する。
