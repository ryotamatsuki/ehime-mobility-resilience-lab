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
- 施設：hospital / clinic / townhall
- ライセンス：ODbL 1.0
- A1.1実行時walking graph：38,860 nodes / 80,102 directed edges
- snap可能な対象施設：8

OSM原抽出物はCIの一時入力とし、Raw取得物をリポジトリへ固定保存しない。

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
3. 到着可能な停留所から徒歩で対象施設へegress
4. 公共交通を使わない徒歩直行経路とも比較

### 現在の明示的制約

- stop間の徒歩transferは未実装
- GTFSにshapes.txtがないため、公開形状は停留所順polylineになる
- 対象範囲はぐるりんおおず停留所範囲周辺であり、愛媛県全域ではない
- 施設はOSM登録状況に依存する
- 本結果はC：モデル推計であり、観測された旅行時間ではない

## 4. Stress Test

シナリオ：`ozu-clockwise-loop-unavailable`

分類：**D：ユーザー仮定**

停止対象：

- route 11：市内循環バス(ぐるりんおおず)右回り
- route 21：市内循環バス(ぐるりんおおず)右回り・土日祝運休便

これは災害時に当該路線が停止すると予測するものではない。ネットワークの感度を確認するStress Testである。

## 5. 実計算結果

GitHub Actions run `32554190506` で、2026-08-21 08:00を出発時刻として実計算した。

対象：

- population zones：1,840
- population in analysis envelope：26,553.4167人相当
- GTFS stops：37 / 37 stopをwalking graphへsnap
- essential facilities：8

### Baseline

| 指標 | 結果 |
|---|---:|
| 30分以内到達人口 | 23,488.2101 |
| 30分以内割合 | 88.456% |
| 60分以内到達人口 | 26,240.9183 |
| 60分以内割合 | 98.823% |
| 90分以内到達人口 | 26,326.7736 |
| 90分以内割合 | 99.146% |
| 人口加重平均所要時間 | 16.702分 |

### 右回り停止後

| 指標 | 結果 |
|---|---:|
| 30分以内到達人口 | 23,421.1285 |
| 30分以内割合 | 88.204% |
| 60分以内到達人口 | 26,240.9183 |
| 60分以内割合 | 98.823% |
| 90分以内到達人口 | 26,326.7736 |
| 90分以内割合 | 99.146% |
| 人口加重平均所要時間 | 16.896分 |

### Impact

- 60分圏人口減少：0人相当
- 30分圏人口減少：約67.0816人相当
- 1分超の所要時間増加人口：約1,365.1575人相当
- 対象人口に占める1分超影響人口：約5.14%
- 人口加重平均所要時間：+0.194分

60分圏だけなら「影響なし」に見える一方、30分圏、連続的な所要時間、影響人口では変化が確認できる。したがって今後の製品UIでは**単一の到達圏閾値だけを主要KPIにしない**。

## 6. 成果物

CIで以下を生成する。

- `summary.json`
- `stops.geojson`
- `facilities.geojson`
- `routes.geojson`
- `population_access.geojson`

GitHub Actions artifact：`a1-1-real-accessibility`

Raw第三者データではなく、再現可能な分析成果物として保存する。

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

## 8. A1.1 Release Gate

- [x] 現行期間内の実GTFSを1フィード固定
- [x] GTFS構造・calendar・service期間を実データで確認
- [x] GTFS 37停留所をOSM徒歩ネットワークへ接続
- [x] 実OSM道路をroutingへ使用
- [x] 実人口データを分母へ使用
- [x] 実OSM施設を目的地へ使用
- [x] 平常時Accessibility計算
- [x] 1つの公共交通停止Stress Test
- [x] Before / After比較
- [x] A/B/C/D分類
- [x] provenance
- [x] unit test
- [x] 実データCI
- [x] 分析成果物artifact保存
- [ ] 愛媛県全域化（A1.1対象外）
- [ ] Synthetic OD（A2対象）
- [ ] Traffic Assignment（A3対象）

A1.1は上記範囲で完成と判定する。
