# A1.3 Independent QA Report

基準日：2026年8月22日（JST）

## 判定

**PASS WITH WARNINGS — mainへのmerge可**

A1.3は、理想UIとして定義した「原因 → 空間 → 結果」の3ペインPlanning Canvasを、A1.1で検証済みの実データAccessibility結果へ接続している。

UI上で操作可能な分析をA1.1で計算済みのBaseline / 右回り停止 / 右回り復旧に限定し、道路閉鎖・Traffic Assignment・物流等を未計算のまま有効な機能として見せていない。

## 1. 実データ契約

GitHub Actions run 32558871252で以下を確認した。

- Python tests: PASS
- A0 foundation checks: PASS
- public data contract: PASS
- deterministic model fixture: PASS
- A1 source probe: PASS
- A1.1 real-data rebuild: PASS
- A1.1 result contract: PASS
- A1.3 site build: PASS
- A1.3 generated-site smoke: PASS
- artifact upload: PASS

判定：PASS

## 2. UIとモデルの意味一致

### Scenario

- Baseline = A1.1 baseline
- Scenario A = route 11 / 21停止のA1.1 disrupted
- Recovery = A1.1 baselineへ戻す操作

Scenario B/C、新規Scenarioはdisabled。

### Map

- 平常時はGTFS路線を青で表示
- Scenario A時のみ停止対象路線を赤破線で表示
- 人口点はBaseline / Disruptedの所要時間、またはdeltaで着色
- 計算済み対象路線の地図PopupからScenario Aへ切替可能

判定：PASS

## 3. Impact Summary

以下はA1.1成果物または `population_access.geojson` から計算する。

- 1分超悪化人口：A1.1 summary
- +1分以上人口：100m人口 × delta
- +5分以上人口：100m人口 × delta
- +10分以上人口：100m人口 × delta
- 60分以内人口：A1.1 summary
- 60分圏脱落人口：A1.1 summary
- 人口加重平均所要時間：A1.1 summary
- 影響地域ランキング：population × delta

新しい交通需要や被害値をUI側で生成していない。

判定：PASS

## 4. Bottom Analytics

### Before / After

`population_access.geojson` の同一メッシュデータからSVGを生成する。

### Distribution

Baseline / Disruptedの各所要時間と人口から、5分刻みの人口加重累積分布をブラウザ上で算出する。

### Recovery

現在検証済みの復旧候補を右回り系統だけに限定し、復旧後はBaselineへ戻す。

複数候補の架空ランキングは生成していない。

判定：PASS

## 5. Data Transparency

画面上に以下を常時表示する。

- A：GTFS
- B：人口・OSM
- C：Accessibility
- D：停止仮定

Provenanceタブではinput data version、model version、parameters、git SHA、limitationsを表示する。

判定：PASS

## 6. 未計算機能の誤認防止

以下はUI上でdisabledまたは「未計算」と表示する。

- 道路区間停止
- 道路容量低下
- 鉄道停止
- 航路・港湾停止
- Scenario B/C
- 新規Scenario

判定：PASS

## 7. Responsive / Accessibility

静的レビューで以下を確認。

- Desktop 3 pane
- Tablet reflow
- Mobile縦並び
- keyboard focus style
- skip link
- button / labelの明示
- 色だけに依存しない停止路線の赤破線表現
- `prefers-reduced-motion`対応
- print CSS

判定：PASS WITH WARNING

Warning：実公開GitHub Pagesでの複数端末・複数ブラウザの視覚回帰テストは、main deploy後に実施する。

## 8. Known Limitations

A1.1から継続する制約：

1. 大洲市ぐるりんおおず停留所範囲周辺のみ。
2. OSM病院は公式医療機関台帳ではない。
3. 人口は令和2年簡易100m按分値。
4. stop-to-stop徒歩transfer未実装。
5. GTFSにshapes.txtがなくstop-order polylineを使用。
6. 右回り停止はD区分の感度分析であり災害被害予測ではない。
7. 道路閉鎖、Synthetic OD、Traffic Assignment、Freight、Reliefは未実装。

## 9. Merge Gate

- [x] Source UI smoke
- [x] JavaScript syntax
- [x] A1.1 real-data rebuild
- [x] Generated A1.3 site smoke
- [x] Manifest stage A1.3
- [x] Raw third-party archiveをPagesへ含めない
- [x] Independent QA
- [ ] QA追加後の最終head CI
- [ ] PR Ready / merge
- [ ] main deploy
- [ ] 公開URL実画面確認

最終head CIがPASSした場合、PR #4はmainへmergeしてよい。
