# A1.11 QA Report — Time-dependent Criticality

判定: **PASS WITH WARNINGS — mainへのmerge可**

## Release Gate

A1.11は次をすべて満たした。

1. A1.9 predecessor outputs（病院・避難所・時間帯・08:00 Criticality）が回帰せず再生成できた — PASS。
2. `time_dependent_criticality.json` が06:00〜21:00の16行を持つ — PASS。
3. 各時刻のroute ranking件数が当日active route総数4と一致 — PASS。
4. 各時刻のtrip ranking件数が当日active trip総数11と一致 — PASS。
5. remaining boardable connection数は時間経過で非増加 — PASS。
6. 終了済みroute/tripは `evaluated=false`・impact=0 — PASS。
7. outageによるBaselineからの不自然なAccessibility改善なし — PASS。
8. 08:00 Top route/tripがA1.8 `criticality.json` と一致 — PASS。
9. peak route/trip eventを実データで確認 — PASS。
10. A1.10 destination switcher predecessor regression smoke — PASS。
11. Planning CanvasがA1.11 stageを受理し16時間帯表を生成 — PASS。
12. client-side routing/geocoding追加なし — PASS。
13. raw official medical/shelter workbookをartifactへ含めない — PASS。
14. Python/source/generated-site smoke — PASS。

## Real-data result

Workflow run: `32603378315`

分析計算時間はおおむね22:46:51〜22:49:15で、A1.9 predecessor再生成を含め約2分24秒だった。

- 時間帯: 06:00〜21:00、1時間刻み、16 slots
- 実行したroute leave-one-out: 39回
- 実行したtrip leave-one-out: 87回
- material route impactあり: 10 slots
- material trip impactあり: 10 slots
- Top routeの時間帯入替: 6回
- Top tripの時間帯入替: 8回

### Peak route event

- 時刻: **11:00**
- route_id: **11**
- route: **市内循環バス(ぐるりんおおず)右回り**
- 1分超悪化人口: **3,370.5401人相当**
- 5分超悪化人口: **2,626.5371人相当**
- 10分超悪化人口: **350.3717人相当**
- 人口加重平均所要時間悪化: **+0.895分**
- 30/60分閾値到達圏損失: 0人相当

### Peak trip event

- 時刻: **11:00**
- trip_id: **11+0+毎日+3**
- route: **市内循環バス(ぐるりんおおず)右回り**
- first departure: **10:00**
- headsign: **市立大洲病院**
- 1分超悪化人口: **3,370.5401人相当**
- 人口加重平均所要時間悪化: **+0.895分**

この結果はA1.7で右回り系統全体の影響最大時刻が11:00だったこととも整合する。

## 08:00 regression

A1.8の既存結果と一致した。

- Top route: route 21「市内循環バス(ぐるりんおおず)右回り・土日祝運休便」
- Top trip: `21+0+土日祝運休便+1`、07:15発、市立大洲病院行
- 1分超悪化人口: 1,955.2890人相当
- 平均悪化: +0.728分

## Predecessor regression

A1.9/A1.10も同runで再確認した。

- 病院: 5
- 指定緊急避難場所: 4
- 指定一般避難所: 13
- 指定福祉避難所: 2
- A1.9 generated-site smoke: PASS
- A1.10 destination-switcher smoke: PASS

## Artifact

- name: `a1-11-planning-canvas`
- artifact ID: `9483524559`
- size: 344,839 bytes
- SHA-256: `3cba7522a4b7c9e9c68474c7a7902033895f282e5f4e8933f765aaf190077317`

## Truthfulness

- 分析目的地: 病院
- Accessibility: Cモデル推計
- route/trip停止: Dストレステスト
- failure probability、ridership、運行重要度、実災害被害を表すとは表示しない。
- 避難所AccessibilityはA1.9のまま保持し、A1.11 Criticality rankingには混在させない。

## Warnings

1. 1時間刻みなので時間帯間の短時間ピークを取りこぼす可能性がある。
2. 各route/trip停止は独立感度分析で、車両運用・連鎖障害・復旧資源制約を含まない。
3. 利用者数、費用、公平性、運行継続上の重要度はrankingに含まれない。
4. A1.11 Criticalityの目的地は病院のみ。避難所Criticalityは未実装。
5. OSMはlive外部データであり、将来更新により細かな値が変動しうる。
