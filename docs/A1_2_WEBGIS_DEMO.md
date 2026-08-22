# A1.2 — Real Accessibility WebGIS Demo

基準日：2026年8月22日（JST）

## 1. 目的

A1.1で完成した実データAccessibilityを、分析コードを読まない利用者でも操作・比較できる最小WebGISへ接続する。

A1.2の目的は機能拡張ではなく、**A1.1の計算内容とUIの意味を一致させること**である。

A1.2では道路閉鎖、Synthetic OD、Traffic Assignment、物流、救援物流、全県GTFS統合には進まない。

## 2. 公開する分析

対象：大洲市「ぐるりんおおず」停留所bbox周辺

目的地：OSM `amenity=hospital`

出発条件：2026-08-21 08:00

比較する2状態：

1. Baseline：対象日の有効GTFS全路線を利用可能
2. Disrupted：右回り系統 route 11 / 21 を利用不能とするD区分Stress Test

A1.1のPython計算結果をGitHub Actionsで再生成し、A1.2はその派生成果物だけを静的Webサイトへコピーする。

Raw GTFS ZIP、Raw人口ZIP、Raw Overpass応答はGitHub Pagesへ配信しない。

## 3. WebGIS機能

- Baseline / 右回り停止の切替
- GTFS路線表示
- 停留所表示
- 病院表示
- 100m人口・Accessibility点表示
- 人口メッシュクリックによる人口、Before時間、After時間、差分確認
- 停止対象路線の明示
- 30 / 60 / 90分圏指標
- 人口加重平均病院アクセス時間
- 1分超悪化人口
- 人口×遅延時間で見た影響上位メッシュへのズーム
- A/B/C/D分類、input version、model version、git SHA、limitations表示

## 4. 表示原則

### 「影響なし」と誤表示しない

今回のStress Testでは30分圏・60分圏人口が変化しない一方、1分超の旅行時間増加人口が存在する。

そのためA1.2は到達圏人口だけをKPIにせず、連続的所要時間と影響人口を同時表示する。

### 未計算機能を操作可能に見せない

A0 UIに存在した「国道56号をクリックして停止」「Traffic / Logistics / Relief」等はA1.2から除外する。

道路閉鎖等は対応する計算Gateを通過したStageでのみ再導入する。

### 対象範囲を全県と誤認させない

画面上部、地図、provenanceに「大洲市ぐるりんおおず停留所範囲周辺」であることを明示する。

## 5. ビルド方式

1. `probe_a1_sources.py` で実入力の取得可能性を確認
2. `build_a1_1.py` でA1.1を再計算
3. `build_a1_2_demo.py` でcleanな `_site` を生成
4. `web/tests/smoke.js _site` で成果物件数・Stage contractを検証
5. mainだけGitHub Pages artifactをdeploy

外部APIの一時失敗に備え、source probeとA1.1 buildはCI内で最大3回再試行する。

## 6. A1.2 Release Gate

- [x] A1.1をmainへ統合
- [x] A1.2をA1.1と別ブランチで開始
- [x] A0の仮道路Stress Test UIを削除
- [x] Baseline / 右回り停止切替
- [x] GTFS route / stop表示
- [x] hospital表示
- [x] population accessibility表示
- [x] mesh単位Before / After表示
- [x] 到達圏だけでなく連続時間差を表示
- [x] provenance / limitations表示
- [x] Raw第三者入力をPagesへコピーしないbuild
- [x] source smoke test
- [x] generated-site smoke test
- [x] 外部入力のretry
- [ ] GitHub Actions最終PASS
- [ ] PR review / merge
- [ ] main Pages deploy確認

最後の3項目を通過してA1.2完了とする。
