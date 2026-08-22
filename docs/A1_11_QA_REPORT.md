# A1.11 QA Report — Time-dependent Criticality

判定: **PENDING — real-data CI待ち**

## Release Gate

A1.11は次をすべて満たした場合のみmainへmergeする。

1. A1.9 predecessor outputs（病院・避難所・時間帯・08:00 Criticality）が回帰せず再生成できる。
2. `time_dependent_criticality.json` が06:00〜21:00の16行を持つ。
3. 各時刻のroute ranking件数が当日active route総数と一致する。
4. 各時刻のtrip ranking件数が当日active trip総数と一致する。
5. 時間経過に伴うremaining boardable connection数が増加しない。
6. 既に終了したroute/tripは `evaluated=false`・impact=0である。
7. outageでBaselineよりAccessibilityが改善するケースがない。
8. 08:00のTop route/tripがA1.8 `criticality.json` と一致する。
9. peak route/trip eventが少なくとも1件存在する。
10. A1.10 destination switcherを維持する。
11. Planning CanvasがA1.11 stageを受理し、16時間帯表を表示できる。
12. client-side routing/geocodingを追加しない。
13. raw official medical/shelter workbookをPages artifactへ含めない。
14. PR headでPython/source/generated-site smokeをすべてPASSする。

## Truthfulness

- 分析目的地: 病院
- Accessibility: Cモデル推計
- route/trip停止: Dストレステスト
- failure probability、ridership、運行重要度、実災害被害を表すとは表示しない。
- 避難所AccessibilityはA1.9のまま保持し、A1.11 Criticality rankingには混在させない。

## Expected regression

08:00はA1.8の既存ランキングと一致することを必須とする。具体的な全日peak時刻・影響人口・Top route/tripは実データCIで確定後、この文書へ追記する。

## CI Result

未実行。最終headのworkflow run、artifact ID、実測peak resultを確認後に更新する。
