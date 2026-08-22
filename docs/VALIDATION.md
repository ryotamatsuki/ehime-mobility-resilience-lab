# Validation Plan and Results

## 方針

実データの取得状態、入力版、モデル版、パラメータ、git_shaを結果ファイルに保存する。入力が不足する場合は指標を生成せず、理由を記録する。

## Data QA

- 必須列と型
- Null、重複、ID一意性
- CRSと緯度経度範囲
- Geometry妥当性
- 参照ID整合性
- GTFSの必須ファイル、stop_times参照、calendar、calendar_dates
- ZIPのパス逸脱、展開数、展開サイズ

## Model QA

- 通勤市町村ペア総量の保存
- 発生・集中margin
- 非通勤ODと貨物ODの分離
- 同一入力・同一設定の決定性
- 障害なしの結果が基準結果と一致すること
- 容量低下・閉鎖の影響方向が説明可能であること
- 未取得データをゼロ値へ黙って置換していないこと

## Traffic metrics

GEH、MAPE、RMSE、screenline、VKTを計算する。低交通量やゼロ観測値ではMAPEだけを品質判定に使わない。

## Holdout

観測リンクを固定ハッシュで80%と20%に分ける。Validationリンクは校正計算から除外し、件数、区分、除外IDを結果に保存する。Calibrationリンク数が少ない場合は、全県と松山都市圏を分けた精度を報告できない状態として明示する。

## 初回実行の事実

R3道路交通センサスEhime CSV、OSM主要道路、R6 500m人口メッシュの取得・形式確認を実行した。国勢調査市町村OD、経済センサス、物流センサス、許諾確認済みの愛媛県全域GTFSは、初回公開bundleへ未投入である。したがって、それらを前提とする精度指標は未算出とする。

決定論的なfixtureでは、IPFの行和・列和・総量保存、BPR静的配分、経路閉鎖、GEH・MAPE・RMSE・VKT、固定holdout分割を実行した。出力は outputs/fixtures/model_validation.json に保存し、fixtureは愛媛県の観測精度を意味しないと明記している。

## Release threshold

閾値は、実観測値の件数と対象地域が確定した後に設定する。fixtureの合格は本県全域のモデル精度を意味しない。実データの結果には、対象範囲、欠損、観測と推計の区分を併記する。
