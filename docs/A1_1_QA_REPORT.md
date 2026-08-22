# A1.1 QA / Red-Team Report

基準日：2026年8月22日（JST）

## 判定

**PASS WITH WARNINGS**

A1.1の目的である「現行の実GTFS 1フィード + 実OSM道路 + 実人口 + 実施設を用いて、平常時と公共交通停止時のAccessibilityを計算し、差分とprovenanceを保存する」は達成した。

A1.1の結果を、愛媛県全域の完成モデル、災害被害予測、観測された旅行時間として扱ってはならない。

## 1. Data QA

### GTFS

- 大洲市公式ページから直接取得：PASS
- feed version：5.0
- feed start：2026-04-01
- feed end：2027-03-31
- 分析日2026-08-21が有効期間内：PASS
- `stops.txt`：37
- `routes.txt`：4
- `trips.txt`：11
- `stop_times.txt`：存在
- `calendar.txt` / `calendar_dates.txt`：存在
- 分析日のactive connections：542
- GTFS validator（本リポジトリ）：PASS
- 37/37停留所をwalking graphへsnap：PASS
- `shapes.txt`：なし。route形状はstop-order polylineで代替し、その制約を明示：PASS WITH WARNING

### Population

- 大洲市令和2年簡易100m人口ZIPを取得：PASS
- source rows：5,478
- 使用zone：1,840
- 使用人口：26,553.4167人相当
- 100m実測人口ではなく簡易按分値であることをB区分として表示：PASS

### OSM

- GTFS stop bbox + 0.02度で道路を取得：PASS
- walking graph：38,860 nodes / 80,102 directed edges
- `amenity=hospital`：7件snap
- OSMは公式病院台帳ではないことを明示：PASS WITH WARNING
- Raw Overpass JSONをGitHubへcommitしていない：PASS

## 2. Model QA

モデル：`minimal-multimodal-v0.1.1`

- OSM道路をwalking networkとして実使用：PASS
- GTFS calendarを解釈：PASS
- GTFS stop_timesをConnection Scanへ投入：PASS
- 徒歩access + transit + 徒歩egress：PASS
- 徒歩直行経路との比較：PASS
- route停止条件をD区分として適用：PASS
- 同一条件で停止によってAccessibilityが改善する不合理な結果が出ないcontract：PASS

未実装：

- stop-to-stop walking transfer
- 複数GTFS feed統合
- 鉄道・フェリー統合
- 公式病院台帳との照合
- 全県Accessibility

これらはA1.1の対象外であり、未実装であることを明示する限りBlockerではない。

## 3. Stress Test QA

D区分シナリオ：`ozu-clockwise-loop-unavailable`

停止対象：route 11 / 21（右回り系統）

これは災害被害予測ではなく、ネットワーク感度確認用のユーザー仮定である。

### Baseline

- 30分圏人口：23,081.0496
- 60分圏人口：26,240.9183
- 90分圏人口：26,326.7736
- 人口加重平均：17.734分

### Disrupted

- 30分圏人口：23,081.0496
- 60分圏人口：26,240.9183
- 90分圏人口：26,326.7736
- 人口加重平均：18.456分

### Impact

- 30分圏人口差：0
- 60分圏人口差：0
- 1分超所要時間増加人口：1,955.289人相当
- 対象人口比：約7.36%
- 人口加重平均所要時間差：+0.722分

固定閾値の到達圏人口だけでは変化を捉えられないことが確認された。今後のUI・KPIは到達圏人口だけでなく、連続的な時間差、影響人口、可能であれば分位点や分布も併記すべきである。

## 4. Automated QA

最終確認系：

- Python unit tests：13 PASS
- A0 foundation checks：PASS
- public data contract：PASS
- deterministic fixture：PASS
- Python compileall：PASS
- Web smoke：PASS
- A1 source probe：PASS
- A1 real accessibility result contract：PASS
- Artifact upload：PASS

成功したreal accessibility artifact：

- Artifact ID：9471023453
- SHA256：`77fecafc0e4648d79d9739408d27fd3e4e94610184a21dddfe94874f4ba77892`

## 5. External Dependency Warning

病院限定版の最初のCI実行ではOverpass APIがHTTP 504 Gateway Timeoutとなった。

同一GitHub Actions jobを再実行したところ、同一コードで成功したため、モデルロジックのFailureではなく外部API一時障害と判定した。

### Required follow-up before Production

- HTTP retry / exponential backoff
- Overpass fallback endpoint
- source checksum
- ライセンスを満たす入力snapshot/cache方式の検討
- CIをライブ外部APIだけに依存させない設計

A1.1ではWarningとし、A1.1 completionのBlockerにはしない。A6 Production Releaseまでには解消対象とする。

## 6. Provenance / Licensing QA

- Ozu GTFS source URL：記録済み
- Ozu GTFS CC BY 4.0：記録済み
- 100m人口 source URL：`https://gtfs-gis.jp/teikyo/` に修正済み
- 人口 CC BY：記録済み
- OSM ODbL 1.0：記録済み
- classification A/B/C/D：記録済み
- model version：記録済み
- analysis date/time：記録済み
- scenario ID：記録済み
- git SHA：artifact provenanceに記録
- Phase B hazard GIS：未使用・未加工・未commit

## 7. Red-Team Findings

### Finding 1 — 古いGTFSを採用するリスク

初期候補の伊予市フィードは完全GTFSだったが、feed有効期限が2025-03-31だったため正式入力から除外した。現行期間内の大洲市feedへ切替済み。

判定：RESOLVED

### Finding 2 — 目的地定義が広すぎる

初期版ではhospital / clinic / townhallのいずれかへの到達としていたため、公共交通停止影響を薄める可能性があった。病院Accessibilityに絞って再計算した。

判定：RESOLVED

### Finding 3 — 閾値指標だけでは影響を見落とす

30/60/90分圏人口は停止前後で同値だが、1,955.289人相当で1分超の所要時間増加、平均+0.722分が確認された。

判定：RESOLVED BY METRIC POLICY

今後、固定閾値だけで「影響なし」と表示してはならない。

### Finding 4 — OSM hospitalは公式施設台帳ではない

A1.1の技術検証には使用できるが、行政版の病院Accessibilityでは公式施設データとの照合が必要。

判定：OPEN WARNING / NEXT A1 STEP

### Finding 5 — ライブOverpass依存

CIの一時504を確認。

判定：OPEN WARNING / BEFORE PRODUCTION

## 8. A1.1 Release Recommendation

A1.1は、限定した目的と明示した制約の範囲で**merge可**と判定する。

次のStepへ進む際はA1.1をそのまま全県化するのではなく、まず以下を独立Gateにする。

1. 公式病院・主要施設データの固定
2. stop-to-stop walking transfer
3. 複数GTFS feedの統合方式
4. shapes欠損時の表示・routing policy
5. Overpass retry / fallback / source versioning
6. A1.1成果物のWebGISへの静的統合
