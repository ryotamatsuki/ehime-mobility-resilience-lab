# A1.6 QA Report — Stop-to-Stop Walking Transfer

判定: **PASS WITH WARNING / merge可**

基準日: 2026-08-22

## 検証対象

- stop-to-stop walking transfer edge生成
- transfer上限・buffer
- Connection Scanへのtransfer relaxation
- disabled routeとの整合
- walking transfer再帰連鎖防止
- same-input no-transfer counterfactual
- 全人口メッシュmonotonicity
- A1.5公式病院Gateの回帰
- public bundle leakage gate
- Planning Canvas / mobile smoke

## PASS

### 1. Unit tests

synthetic fixtureで、徒歩transferがない場合60分の経路が、

`bus t1 → 5分transfer（徒歩4分 + buffer1分）→ bus t2 → egress`

により28分になることを確認した。

第2便をdisabled routeにすると60分へ戻るため、transferによって運休設定を迂回しない。

### 2. Transfer edge生成

実OSM walking network・実GTFS 37 stopsで:

- candidate ordered pairs: 1,332
- transfer edges: 156
- outgoing transferあり: 37 / 37 stops
- mean network walk: 6.394分
- max network walk: 9.999分

となり、設定した徒歩10分上限を超えるedgeは生成されていない。

### 3. Transfer chaining gate

walking transferからさらにwalking transferを再帰relaxしない。

10分以下のedgeを連続させてtransfer徒歩上限を実質的に迂回する挙動を禁止した。

### 4. Same-input comparison

同一run内でtransferなし/ありを両方計算しているため、入力データ更新の影響を混入させずモデル変更だけを比較できる。

全1,840人口メッシュについて:

- transfer導入後に有限経路が到達不能へ悪化しない
- transfer導入後の最早到着がno-transferより遅くならない

をビルダーで検証した。

### 5. Official hospital gate regression

- official active hospitals: 5
- verified OSM hospitals: 5
- unmatched official hospitals: 0
- duplicate/unverified OSM features excluded: 2
- raw official workbook published: false
- official raw attributes in public GeoJSON: false

A1.5の保守的ライセンス境界を維持した。

### 6. Scenario regression

A1.6実データ結果:

- population: 26,553.4167人相当
- +1分超悪化人口: 2,030.3675人相当
- mean travel-time degradation: +0.732分
- 30分到達圏減少: 0
- 60分到達圏減少: 0

### 7. CI

PR #7 run 109で以下をPASS:

- Python unit tests
- A0 foundation checks
- public data contract
- deterministic model fixture
- Python compileall
- source Web smoke
- real source probes
- official medical registry compact probe
- A1.6 real-data build
- A1.6 result contract
- generated Planning Canvas smoke
- mobile contract
- official-data leakage checks

## Warning

### W1. 現在の実データ縦切りではKPI改善が0

transfer edgeは156本生成されたが、今回の「ぐるりんおおず・08:00・病院アクセス」ではwalking transferを採用することで最短所要時間が短くなる人口メッシュはBaseline/Scenarioとも0だった。

これは実装失敗ではない。synthetic fixtureではtransferを介した後続便乗車が実際に最短経路になることを確認済みである。

一方、**real-data validationとしてはtransferが最短経路に選択されるケースをまだ観測できていない**ため、より複数路線・乗換機会があるGTFSへ拡張した時点で再度実データ検証する必要がある。

### W2. Transfer parameterはモデル設定値

10分上限と1分bufferはA1.6の透明なモデル仮定であり、事業者が公式に保証する乗換時間ではない。

### W3. 完全なJourney Plannerではない

`transfers.txt`、Pathways、駅構内、wheelchair、勾配・階段、信号待ち等は未実装。

## Blocker

なし。

## 次Step候補

A1.6の次は、transferの実データ外的妥当性を高めるため、**A1.7 Multi-feed / Multi-route Validation** を推奨する。

1つの小規模循環バスだけでモデル仕様を決め切らず、複数路線・乗換が実在する公開GTFSを追加し、walking transferが実際の最短経路へ入るケースを確認する。その後A1の県内拡張へ進む。
