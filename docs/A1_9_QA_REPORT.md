# A1.9 QA Report — Shelter Accessibility

判定: **PASS WITH WARNINGS — final head CI通過を条件にmainへmerge可**

## Release Gate

A1.9のRelease Gateは次を満たすこととする。

1. 大洲市公式避難所ExcelをCI中に取得できる。
2. 公式3シートを認識し、市全体件数60 / 96 / 20を取得できる。
3. Raw Excelをrepository、artifact、GitHub Pagesへ含めない。
4. 公式データに座標がないことを前提に、外部ジオコーダーや推測座標を使用しない。
5. OSM named featureとの一意照合に成功した施設だけをAccessibilityへ投入する。
6. 緊急避難場所・一般避難所・福祉避難所の3種すべてで、少なくとも1施設以上が道路NWへsnapできる。
7. Baselineより運休シナリオのAccessibilityが不自然に改善しない。
8. A1.5病院公式Gate、A1.6徒歩乗換、A1.7時間帯分析、A1.8 Criticalityが回帰しない。
9. Planning Canvas生成物と公開データ契約がsmoke testを通る。

## Data Gate結果

公式データ:

- 大洲市「避難所等一覧」
- 更新時点: 2026-04-01
- CC BY 4.0

確認件数:

- 指定緊急避難場所: 60
- 指定一般避難所: 96
- 指定福祉避難所: 20

公式Excelに緯度経度列は存在しない。位置は公式値として扱わない。

## OSM位置照合Gate結果

現在のぐるりんおおずGTFS分析範囲で、一意のOSM named featureまで照合し、徒歩道路NWへ0.5km以内でsnapできた件数:

- 指定緊急避難場所: 4
- 指定一般避難所: 13
- 指定福祉避難所: 2
- 合計: 19

曖昧一致:

- 指定緊急避難場所: 0
- 指定一般避難所: 1
- 指定福祉避難所: 1

曖昧一致は計算対象から除外した。

注意: 市全体公式件数60 / 96 / 20は分析範囲内施設数ではない。公式データに座標がないため、4/60等を分析範囲内の照合率として評価しない。

## 代表的な位置照合の確認

実成果物を確認し、次のような名称対応を確認した。

### 緊急避難場所

- 冨士山公園 ↔ 冨士山公園
- 徳森公園 ↔ 徳森公園
- 県立大洲高等学校運動場 ↔ 県立大洲高等学校
- 県立大洲農業高等学校運動場 ↔ 県立大洲農業高等学校

後者2件は `parent_feature` として扱う。学校所在地を避難場所の代表位置として用いるが、運動場そのものの正確な代表点ではない。

### 一般避難所

大洲小学校、大洲南中学校、平野中学校、平野小学校、喜多小学校、平小学校、大洲北中学校、新谷小学校、新谷中学校、菅田小学校、肱東中学校等について、市立等の表記差を許容しつつ一意照合された。

### 福祉避難所

- 特別養護老人ホームとみす寮
- 大洲育成園

公式Excelには一部の施設名・住所にふりがなが同一セル内へ連結されているため、名称正規化後に照合した。

## Accessibility結果

08:00 Baseline / 右回り route 11・21運休Stress Test:

| Destination | 使用施設 | Baseline 30分圏 | Scenario A 30分圏 | 1分超悪化人口 | 平均悪化 |
|---|---:|---:|---:|---:|---:|
| 指定緊急避難場所 | 4 | 20,789.8079 | 20,381.2975 | 1,035.1204 | +0.201分 |
| 指定一般避難所 | 13 | 25,055.4109 | 25,053.2837 | 1,375.3316 | +0.230分 |
| 指定福祉避難所 | 2 | 15,090.5726 | 15,064.1391 | 981.8614 | +0.230分 |

全3種で次を確認した。

- Baseline 30分圏人口 >= Scenario A 30分圏人口
- Baseline 60分圏人口 >= Scenario A 60分圏人口
- 人口加重平均所要時間悪化 >= 0

## Regression Gate

A1.9実データCIで次を再実行しPASSした。

- Python unit tests
- A0 foundation checks
- public data contract validation
- deterministic fixture models
- Python syntax compile
- GTFS / population / OSM source probe
- 愛媛県公式病院台帳probe
- 大洲市公式避難所Excel probe
- A1.8 Route / Trip Criticality再計算
- A1.7 16時間帯profile再計算
- A1.6徒歩乗換network
- A1.5公式病院照合
- A1.9避難所Accessibility
- Planning Canvas生成
- generated-site smoke test
- artifact upload

実データCI run `32582653196` の主要ステップはPASSした。最終documentation headについても同じGateを再実行してからmergeする。

## Public Bundle Gate

公開対象:

- `shelters.geojson`
- `shelter_accessibility.json`
- `shelter_population_access.geojson`
- `summary.json`
- 既存A1成果物

非公開:

- 大洲市公式避難所Raw Excel
- 愛媛県公式医療機関Raw Excel
- Raw Overpass JSON

A1.9では避難所位置の公開GeoJSONは生成するが、Planning CanvasのLeaflet地図に避難所レイヤーを切り替え表示する機能は未実装である。manifest capabilityは `shelter-public-geojson` とし、`shelter-map-layer` を名乗らない。

## Warnings

1. 分析範囲は大洲市全域ではなく、ぐるりんおおずGTFS停留所bbox周辺である。
2. 公式避難所名簿に座標がないため、OSM位置照合済みsubsetのみを計算している。
3. `parent_feature`は親施設位置であり、運動場等の厳密な入口位置ではない。
4. 公式Excelの一部名称・住所にはふりがな連結があり、正規化処理を介している。
5. OSM/Overpassは実行時外部依存であり、503/504等に備えてCI retryが必要である。
6. 人口は簡易100m按分値である。
7. 収容人数はA1.9では容量制約として使用していない。
8. ブラウザ上の複数環境・実端末による視覚回帰テストは本QAでは実施していない。

以上から、A1.9は分析ロジック・データ契約・生成Web成果物について **PASS WITH WARNINGS** とする。
