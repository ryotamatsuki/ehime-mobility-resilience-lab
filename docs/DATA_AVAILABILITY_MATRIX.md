# Data Availability Matrix

調査基準日：2026年8月22日（JST）

可用性は、データの存在だけでなく、利用許諾、更新性、空間粒度、Phase Aの計算へ投入できる状態までを含めて判定する。

| Function | Required Data | Available | Expected accuracy | Main risk | A1以降のGate |
|---|---|---:|---|---|---|
| Transit accessibility | 県内事業者のGTFS static、calendar、shapes | △（A1.1部分○） | B/C | 大洲市ぐるりんおおずは現行GTFSで実計算PASS。県内全域網羅は未確認 | A1.1は2026-04-01〜2027-03-31 feed version 5.0を固定。全県拡張時はfeedごとにGate |
| GTFS-Realtime | VehiclePosition、TripUpdates、Alert | △ | A/B | API key、鮮度、長期保存条件 | Phase Aでは固定スナップショットの可否を確認 |
| Rail accessibility | 鉄道GTFSまたは正式時刻表 | ×〜△ | 未確定 | JR四国等のGTFS公開範囲を確認できていない | 未確認路線を存在するものとして補完しない |
| Ferry accessibility | 航路・便・港湾接続GTFS | △ | B/C | ODPT公開は個別データ、県内全航路の網羅性未確認 | route_type、港湾接続、shape欠損を確認 |
| Road accessibility | OSM道路ネットワーク | ○ | B/C | 全県モデルは道路属性・規模が大きい | A1.1でGTFS bbox周辺のOSM walking graphを実取得・実routing済み。全県拡張は別Gate |
| Road capacity | OSM lanes、maxspeed、道路交通センサス | △ | B/C | 容量・速度の既定値が仮定、リンク対応は加工 | default値、車種制約、観測リンク対応を固定 |
| Observed traffic | R3道路交通センサス | ○ | A/B | 2021年基準、観測・非観測、方向、時間帯の扱い | 調査区間とOSMリンクの対応方法をQA |
| Commuting OD | R2国勢調査市町村間通勤・通学OD | △ | A/B | 取得版・表番号・秘匿・県内詳細粒度が未確定 | 市町村間総量を固定する実ファイルを登録 |
| Automobile OD | R3自動車起終点調査 | △ | A/B | 公開集計は都道府県間等で、県内細粒度ODではない | gateway制約として使用範囲を固定 |
| Population | MLIT R6 500m + A1.1 simplified 100m | ○ | B | 100m値は簡易按分で実測セル人口ではない | A1.1は大洲市100m 5,478 rowsを実取得。分母の性質をUIに表示 |
| Facilities | OSM + 将来の公式施設 | ○（A1.1）/ △（全県） | B | OSM登録状況・現行性 | A1.1はhospital/clinic/townhallを実取得。防災拠点病院等は公式一覧照合後に追加 |
| Economic census | R3経済センサス500m・1km mesh | △ | B/C | 従業者は目的地魅力度でありトリップ量や在庫ではない | 実ファイル・表・産業分類を登録 |
| Freight demand | 全国貨物純流動調査、道路交通センサス大型車 | △ | A/B/C | 県内細粒度貨物OD、在庫、企業間流動がない | 相対指標と絶対量を分離 |
| Warehouses | Project LINKS、県公開施設 | △ | B | 個別ライセンス、項目、現行性、再配布が未確認 | dataset licenseと位置精度を個別確認 |
| Ports | 愛媛県港湾統計、許諾済み港湾ノード | △ | A/B | 統計は集計値であり、港湾形状・運用能力ではない | ノード化の加工方法とデータ年を固定 |
| Relief logistics | 避難所、広域防災拠点、物資集積、備蓄 | △ | B/C | 住所・座標、更新日、数量、現行性が不均一 | 公式位置と数量の別管理 |
| Disaster base hospitals | 現行指定一覧、医療機関GIS | △ | B | 古い国土数値情報と現行指定の差 | 現行一覧の公式照合 |
| Phase B hazard adapter | 愛媛県新地震被害想定GIS | × | blocked | 許諾前の加工・派生・公開禁止 | Written permission Gate PASSのみ |

## 可用性の意味

- ○：取得・利用条件・最低限の構造を確認し、計算入力として登録済み。
- △：存在または利用可能性の一部を確認したが、規約、取得版、網羅性、構造、更新性のいずれかが未確定。
- ×：現時点で公開計算入力として扱わない、またはPhase Bの許諾待ち。

## A1.1到達点

1. 大洲市「ぐるりんおおず」GTFSを現行feedとして固定し、実データvalidatorと時刻依存計算をPASSした。
2. GTFS停留所bbox周辺のOSM道路を徒歩ネットワークに変換し、37/37停留所をsnapした。
3. 大洲市令和2年簡易100m人口を分母として1,840 population zonesを実計算に投入した。
4. OSM施設を目的地にしてBaseline / Transit disruptionを比較した。
5. A1.1の結果はC、停止条件はDとしてprovenanceを保存した。

## 次のA1 Gate

A1.1の成功をそのまま全県精度の証明とはしない。次のStepでは、対象GTFS・施設・人口範囲を追加する前に、A1.1の目的地定義、徒歩transfer、複数feed統合、shapes欠損の扱いを独立にレビューする。
