# A1.2 Independent QA Report

基準日：2026年8月22日（JST）

## 判定

**PASS WITH WARNINGS — mainへのmerge可**

A1.2は、A1.1で検証済みの実データAccessibility結果を、計算内容と矛盾しない最小WebGISへ接続するというStage目的を満たしている。

道路閉鎖、Synthetic OD、交通量配分、物流、救援物流、全県GTFS統合を未実装のまま操作可能に見せるA0仮UIは除去した。

## 1. データ整合性

- 大洲市「ぐるりんおおず」GTFSをCI実行時に公式URLから再取得する。
- feed version、有効期間、必須GTFSファイル、calendar/serviceをA1.1 validatorで確認する。
- 37/37停留所がOSM徒歩ネットワークへsnapされることをCI contractで要求する。
- 病院、人口メッシュ、路線、停留所のWebGIS feature件数がA1.1 summaryと一致することをgenerated-site smoke testで確認する。
- Raw GTFS ZIP、Raw人口ZIP、Raw Overpass応答はPages成果物に含めない。

判定：PASS

## 2. モデルとUIの意味一致

- Baselineは対象日の有効GTFS全路線を利用可能とする。
- Disruptedはroute 11 / 21を利用不能とするD区分仮定である。
- 平常時は全運行路線を同じ青色で表示し、停止シナリオ選択時だけ停止対象を赤破線にする。
- 人口メッシュクリックでBaseline / Disrupted / deltaを同時確認できる。
- 30分・60分到達圏人口が変わらない場合でも、1分超悪化人口と平均所要時間差を表示する。
- 地震・豪雨等の実被害予測ではないことを画面上で明示する。

判定：PASS

## 3. 対象範囲の誤認防止

- 画面上で「大洲市ぐるりんおおず停留所範囲周辺」と明示する。
- 愛媛県全域のAccessibility結果とは表示しない。
- 未計算のTraffic / Logistics / Relief等を表示モードとして残さない。
- 次Stage対象は「未計算」と明示し、操作可能なUIを置かない。

判定：PASS

## 4. Provenance / 説明可能性

画面から以下を確認できる。

- input_data_versions
- source URL
- A/B/C/D分類
- model_version
- scenario_id
- parameters
- generated_at_utc
- git_sha
- limitations

判定：PASS

## 5. CI / 再現性

PR CIでは以下をGateとする。

1. Python unit tests
2. A0 foundation checks
3. data contract validation
4. source Web UI syntax / smoke test
5. real-source probe
6. A1.1実データ再計算
7. A1.1 result contract
8. A1.2 clean site build
9. generated A1.2 site syntax / smoke test
10. artifact保存

外部APIの一時的な504等に備え、source probeと実データbuildは最大3回まで再試行する。

判定：PASS

## 6. Security / Web表示

- GeoJSON由来の名称等をHTMLへ挿入する箇所ではescape処理を行う。
- 公開サイトにAPI keyや認証情報を持たせない。
- GitHub Pagesでは重いrouting計算を行わず、検証済み派生成果物だけを表示する。

判定：PASS

## 7. Warnings

### W1 OSM病院は公式病院台帳ではない

A1.2の目的地はOSM `amenity=hospital` であり、行政上の病院一覧、災害拠点病院指定、診療能力を保証しない。

次の施設精度Gateで公式施設一覧と照合する。

### W2 stop間徒歩transferは未実装

A1.1の最小モデルでは、GTFS停留所間の徒歩乗換を一般化していない。複数feed統合前にtransfer modelを独立レビューする。

### W3 GTFS route形状はstop-order polylineを含む

対象feedの形状不足時は停留所順polylineを用いる。道路上の正確な運行軌跡とは表示しない。

### W4 100m人口は簡易按分値

100mセル値は実測人口ではない。B区分の加工データとして「人相当」と表示する。

### W5 OSMタイルはPoC用途

現状はOpenStreetMap標準タイルを背景表示する。アクセス量が増える本番運用ではOSM tile usage policyに従い、適切なタイル提供方法へ切り替える。

### W6 外部入力の可用性

GTFS、人口データ、Overpassの外部配信停止時はCI再計算が失敗する可能性がある。A1.2ではretryを実装済みだが、将来は入力versionの安全なキャッシュ／更新管理を設計する。

## 8. 次Stageへ持ち越す事項

A1.2完了をもって以下が検証済みになったとは扱わない。

- 愛媛県全域GTFSカバレッジ
- 鉄道Accessibility
- 道路閉鎖による公共交通経路変化
- Synthetic OD
- 交通量配分・混雑
- 物流
- 救援物流
- ハザードGIS連携

各項目は独立Gateを設ける。

## 最終判定

A1.2のStage目的に対し、重大なBlocking defectは確認しない。

**Release judgment: PASS WITH WARNINGS / merge可**
