# A1.6 — Stop-to-Stop Walking Transfer

基準日: 2026-08-22

## 目的

A1.5までの時刻依存ルーティングは、人口メッシュから各GTFS停留所への徒歩accessと、降車停留所から病院への徒歩egressは扱っていたが、公共交通利用中の「停留所Aで降車 → 徒歩 → 近接する停留所Bから別便へ乗車」を扱っていなかった。

A1.6ではOSM pedestrian network上の最短徒歩時間からstop-to-stop transfer edgeを生成し、Connection Scanへ組み込む。

## Transfer仕様

- 徒歩速度: 4.8 km/h
- transfer対象: OSM pedestrian network上で徒歩10分以内の異なるGTFS停留所
- transfer余裕時間: 徒歩時間に固定1分を加算
- edge: 有向
- originから停留所へのaccess上限: 従来どおり20分
- stop-to-stop walking transferの再帰連鎖: 禁止

再帰連鎖を禁止する理由は、「A→B 8分、B→C 8分」のような短いstop hopを連続させ、実質16分以上歩くことで10分上限を迂回する挙動を防ぐためである。AからCが道路ネットワーク上10分以内なら直接transfer edgeが生成される。

## Connection Scanへの統合

公共交通connectionでstopへ到着して到着時刻が改善したときだけ、そのstopからのwalking transferを1段relaxする。

transfer先stopの到着時刻は:

`transit arrival + network walk time + 1 minute buffer`

で更新する。その時刻より後に出発するGTFS便は通常のConnection Scanで乗車可能になる。

originから各stopへの徒歩accessは既に道路ネットワークで直接計算しているため、初期accessに対してwalking transferを連鎖させない。

## Same-input Counterfactual

A1.6は同一CI run・同一入力で次の2モデルを必ず計算する。

1. walking transferなし
2. walking transferあり

これにより、OSM更新や施設データ更新による差と、transferロジック追加による差を分離する。

各人口メッシュの公開成果物には、transferありのBaseline/Scenario値に加え、比較用の`baseline_no_transfer_minutes`、`disrupted_no_transfer_minutes`を保持する。

## 2026-08-22 実データ結果

入力はA1.5と同じ。

- 大洲市「ぐるりんおおず」GTFS v5.0
- 37 stops
- 4 routes
- 11 trips
- 542 active connections
- OSM walking graph: 38,860 nodes / 80,102 directed edges
- 公式台帳照合済みOSM病院: 5
- 人口メッシュ: 1,840 cells / 26,553.4167人相当

生成されたwalking transfer network:

- candidate ordered stop pairs: 1,332
- directed transfer edges: 156
- outgoing transferを持つstop: 37 / 37
- 平均network walk: 6.394分
- 最大network walk: 9.999分

## モデル効果

今回の「2026-08-21 08:00出発・病院Accessibility」という実データ縦切りでは、walking transferを追加しても最短到達時間が改善する人口メッシュは0だった。

Baseline:

- improved zones: 0
- improved population: 0人相当
- weighted mean reduction: 0.000分

右回り運休Scenario:

- improved zones: 0
- improved population: 0人相当
- weighted mean reduction: 0.000分

したがってA1.6のScenario impactは同一入力のno-transferモデルと同値で、右回り運休による1分超悪化人口は2,030.3675人相当、人口加重平均悪化は+0.732分である。

これは「walking transferが一般に不要」という意味ではない。現在の小規模循環バス・単一出発時刻・病院目的地という組合せでは、生成されたtransfer edgeを使う経路が既存のaccess/transit/egress経路を上回らなかった、という限定的結果である。

## 検証

synthetic unit fixtureでは次を確認した。

- 1便目でs1→s2
- s2→s3を徒歩4分 + buffer 1分
- s3から2便目へ乗車
- transferなしでは60分、transferありでは28分

したがってtransfer relaxationが実際に後続便乗車へ使われることを決定論的テストで確認している。

また全1,840人口メッシュについて、walking transfer追加後の最早到着時間がno-transfer値より悪化しないmonotonicity gateをビルダー内部で検証する。

## 制約

未実装:

- GTFS `transfers.txt`の事業者指定transfer ruleとの統合
- GTFS Pathways
- 駅構内移動
- wheelchair accessibility
- 横断歩道待ち時間
- 勾配・階段ペナルティ
- リアルタイム遅延を考慮したtransfer

A1.6はこれらを扱う完全なJourney Plannerではない。
