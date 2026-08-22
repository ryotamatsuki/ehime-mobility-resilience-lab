# A1.1 — Minimal Real-Data Accessibility

基準日：2026年8月22日（JST）

## 1. 目的

A1全体へ進む前に、**実GTFS 1フィード + 実OSM道路 + 実人口 + 実施設**だけで、平常時と公共交通障害時のAccessibility差分を再現可能に計算できることを確認する最小縦切りである。

A1.1ではSynthetic OD、Traffic Assignment、貨物、救援物流、Phase BハザードGISは扱わない。

## 2. 採用した実データ

### 大洲市「ぐるりんおおず」GTFS

- 公表主体：大洲市
- 公式ページ：https://www.city.ozu.ehime.jp/site/opendata/44871.html
- 更新日：2026-04-01
- ライセンス：CC BY 4.0
- feed version：5.0
- feed有効期間：2026-04-01〜2027-03-31
- stops：37
- routes：4
- trips：11
- A1.1分析日（2026-08-21）のconnection：542

Raw ZIPはGitHubへ保存せず、CI実行時に公式URLから取得・検証する。

### 令和2年簡易100mメッシュ人口（大洲市）

- 提供：地域・交通データ研究所
- 説明：https://gtfs-gis.jp/teikyo/
- 原統計：令和2年国勢調査250mメッシュ人口を建物等に基づき100mへ簡易按分
- ライセンス：CC BY
- 大洲市source rows：5,478

この人口は100mセルの実測人口ではない。A1.1では**B：公式統計等に基づく加工データ**として扱う。

### OpenStreetMap

- 道路：GTFS全停留所bbox + 0.02度の範囲
- 目的地：`amenity=hospital`
- ライセンス：ODbL 1.0
- A1.1実行時walking graph：38,860 nodes / 80,102 directed edges
- snap可能な病院：7

確認された名称付き病院には、市立大洲病院、喜多医師会病院、北斗会大洲中央病院、恕風会大洲記念病院、静心会平成病院が含まれる。ほかにOSM上で名称未登録のhospitalが2件ある。

OSM原抽出物はCIの一時入力とし、Raw取得物をリポジトリへ固定保存しない。病院情報はOSM登録状況に依存し、公式病院台帳ではない。

## 3. モデル

### Walking

OSM highwayから徒歩グラフを構築する。

- 歩行速度：4.8 km/h
- motorway / motorway_link / construction / proposed等を除外
- access=no/private、foot=noを除外
- 徒歩edgeは双方向化

### Transit

GTFSのcalendar / calendar_datesを解釈し、指定日の有効tripだけを利用する。

A1.1は依存ライブラリを増やさない最小実証としてConnection Scanを実装した。

1. 人口メッシュから徒歩20分以内で到達可能な停留所へアクセス
2. GTFS stop_timesのconnectionを時刻順に走査
3. 到着可能な停留所から徒歩で病院へegress
4. 公共交通を使わない徒歩直行経路とも比較

### 現在の明示的制約

- stop間の徒歩transferは未実装
- GTFSにshapes.txtがないため、公開形状は停留所順polylineになる
- 対象範囲はぐるりんおおず停留所範囲周辺であり、愛媛県全域ではない
- 病院はOSM登録状況に依存し、公式病院一覧ではない
- 本結果はC：モデル推計であり、観測された旅行時間ではない
- OSMはCI実行時のライブ取得であるため、A1.1段階では完全な入力スナップショット再現性を保証しない。Productionまでにchecksum / snapshot provenanceを強化する

## 4. Stress Test

シナリオ：`ozu-clockwise-loop-unavailable`

分類：**D：ユーザー仮定**

停止対象：

- route 11：市内循環バス(ぐるりんおおず)右回り
- route 21：市内循環バス(ぐるりんおおず)右回り・土日祝運休便

これは災害時に当該路線が停止すると予測するものではない。ネットワークの感度を確認するStress Testである。

## 5. 実計算結果

GitHub Actions run `32554426031` の成功した再実行jobで、2026-08-21 08:00を出発時刻として病院Accessibilityを実計算した。

対象：

- population zones：1,840
- population in analysis envelope：26,553.4167人相当
- GTFS stops：37 / 37 stopをwalking graphへsnap
- hospital destinations：7

### Baseline

| 指標 | 結果 |
|---|---:|
| 30分以内到達人口 | 23,081.0496 |
| 30分以内割合 | 86.923% |
| 60分以内到達人口 | 26,240.9183 |
| 60分以内割合 | 98.823% |
| 90分以内到達人口 | 26,326.7736 |
| 90分以内割合 | 99.146% |
| 人口加重平均所要時間 | 17.734分 |

### 右回り停止後

| 指標 | 結果 |
|---|---:|
| 30分以内到達人口 | 23,081.0496 |
| 30分以内割合 | 86.923% |
| 60分以内到達人口 | 26,240.9183 |
| 60分以内割合 | 98.823% |
| 90分以内到達人口 | 26,326.7736 |
| 90分以内割合 | 99.146% |
| 人口加重平均所要時間 | 18.456分 |

### Impact

- 30分圏人口減少：0人相当
- 60分圏人口減少：0人相当
- 1分超の所要時間増加人口：約1,955.289人相当
- 対象人口に占める1分超影響人口：約7.36%
- 人口加重平均所要時間：+0.722分

30分・60分・90分という固定閾値だけを見ると「影響なし」に見える一方、連続的な所要時間と影響人口では劣化が確認できる。したがって今後の製品UIでは、**単一の到達圏閾値だけを主要KPIにせず、影響人口・平均所要時間差・分布変化を併記する**。

## 6. 成果物

CIで以下を生成する。

- `summary.json`
- `stops.geojson`
- `facilities.geojson`
- `routes.geojson`
- `population_access.geojson`

GitHub Actions artifact：`a1-1-real-accessibility`

成功したartifact：

- Artifact ID：9471023453
- SHA256：`77fecafc0e4648d79d9739408d27fd3e4e94610184a21dddfe94874f4ba77892`

Raw第三者データではなく、再現可能性を高めた分析成果物として保存する。

## 7. Provenance

各結果に以下を保持する。

- input dataset IDs
- source URLs
- classification A/B/C/D
- license
- model version
- analysis date / departure time
- scenario id
- parameters
- generated_at
- git SHA
- limitations

A1.1ではライブOSM入力のchecksum/snapshot保持が未完成であり、Production Releaseまでの改善項目とする。

## 8. QAで確認した事項

- 初回の病院版CIではOverpass APIがHTTP 504となり失敗した
- 同一jobの再実行では成功し、モデル計算・結果contract・artifact保存までPASSした
- したがってこれはモデル不具合ではなく外部API一時障害と判定する
- 次Step以降でretry / fallback endpoint / input cacheの導入を検討する

## 9. A1.1 Release Gate

- [x] 現行期間内の実GTFSを1フィード固定
- [x] GTFS構造・calendar・service期間を実データで確認
- [x] GTFS 37停留所をOSM徒歩ネットワークへ接続
- [x] 実OSM道路をroutingへ使用
- [x] 実人口データを分母へ使用
- [x] 実OSM病院を目的地へ使用
- [x] 平常時Accessibility計算
- [x] 1つの公共交通停止Stress Test
- [x] Before / After比較
- [x] A/B/C/D分類
- [x] provenance
- [x] unit test
- [x] 実データCI
- [x] 分析成果物artifact保存
- [x] 外部API一時障害をQA上のWarningとして記録
- [ ] 愛媛県全域化（A1.1対象外）
- [ ] Synthetic OD（A2対象）
- [ ] Traffic Assignment（A3対象）

A1.1は上記範囲で完成と判定する。
