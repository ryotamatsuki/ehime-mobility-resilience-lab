# A1.3 — Ideal Planning Canvas UI

基準日：2026年8月22日（JST）

## 1. 目的

A1.1/A1.2で検証済みの実データAccessibilityを、最終プロダクトの理想形に近い「交通レジリエンス・プランニングキャンバス」へ載せ替える。

参考思想は以下。

- Remix型：地図とScenario Builderを同じキャンバスに置く
- Conveyal型：AccessibilityのBefore / Afterと連続的な所要時間分布を重視する
- UrbanFootprint型：Baseline / Scenario / Recoveryを上部で切り替える
- StreetLight型：通常利用者には数クリックだけ要求し、モデル設定を前面に出さない

A1.3はUI/UX Stageであり、A1.1の分析モデルやデータ範囲を勝手に拡張しない。

## 2. 画面構成

### Header

- プロダクト名
- データ情報
- 共有
- 印刷・レポート
- 分析条件
- ヘルプ

### Scenario Ribbon

- Baseline
- Scenario A：ぐるりんおおず右回り運休
- Scenario B/C：未計算としてdisabled
- Recovery：右回り復旧
- 新規Scenario：Scenario Save実装前はdisabled

### 3 Pane Canvas

左：Scenario Builder

中央：Map

右：Impact Summary / Detail / Report

因果関係を「原因 → 空間 → 結果」の画面配置で表現する。

### Bottom Analytics

1. Before / After簡易空間比較
2. 人口加重所要時間分布
3. Recovery効果

## 3. 実装済み操作

- Baseline / Scenario A切替
- 右回り運休checkbox → 分析表示
- 地図上の計算済み対象路線からScenario Aへ切替
- 所要時間表示 / 差分表示
- 人口メッシュクリックによるBefore / After詳細
- 影響上位メッシュへの地図移動
- 1分 / 5分 / 10分以上の悪化人口を実データからクライアント側集計
- 人口加重累積所要時間分布を実データから生成
- 右回りを復旧してBaselineへ戻すRecovery操作
- Web Share / URLコピー
- ブラウザ印刷
- Provenance / limitations表示

## 4. データ誠実性ルール

理想UI画像に存在した機能でも、現在未計算のものは動くように見せない。

以下はdisabled / 未計算とする。

- 任意道路通行止め
- 道路容量50%
- 任意鉄道区間停止
- 任意航路・港湾停止
- 複合Scenario B/C
- 複数復旧候補ランキング
- Synthetic OD
- Traffic Assignment
- Freight / Relief

RecoveryはA1.1で存在する2状態を利用し、右回りを復旧するとBaselineへ戻ることだけを表示する。

## 5. KPI

到達圏人口だけで影響を判断しない。

右側Impact Summaryでは以下を表示する。

- 1分超悪化人口
- 5分以上悪化人口
- 10分以上悪化人口
- 60分以内到達人口
- 60分圏から脱落した人口
- 人口加重平均所要時間
- 影響上位人口メッシュ

5分・10分閾値は `population_access.geojson` の各メッシュの `delta_minutes` と `population` から集計する。

## 6. 可視化

### Map

Baseline：病院までの所要時間で人口点を着色。

Scenario A：停止後所要時間で着色。

差分表示：

- 灰：変化なし
- 黄：0〜1分
- 橙：1〜5分
- 濃橙：5〜10分
- 赤：10分超

停止対象GTFS路線はScenario A時だけ赤破線で表示する。

### Before / After

A1.1成果物からブラウザ上で簡易SVGを生成する。新しい数値モデルは使用しない。

### Distribution

100m人口メッシュを人口重みとして、Baseline / Scenario Aの累積人口分布を5分刻みで描画する。

## 7. Responsive

- Desktop：左318px / 地図flex / 右370px + 下段3分析パネル
- Tablet：左 + 地図、Impactを下段へ
- Mobile：Builder → Map → Impact → Analyticsの縦並び

## 8. A1.3 Release Gate

- [x] A1.2をmainへ統合した状態から専用branchを開始
- [x] 3ペインPlanning Canvas
- [x] Scenario Ribbon
- [x] 実データに基づくScenario Aだけ操作可能
- [x] 未計算機能をdisabled表示
- [x] Map driven Scenario selection
- [x] Impact Summary
- [x] 1 / 5 / 10分悪化人口
- [x] Before / After簡易分布
- [x] 人口加重所要時間分布
- [x] Recovery操作
- [x] Provenance / Limitations
- [x] responsive CSS
- [x] A1.3 manifest contract
- [x] source/generated-site smoke test更新
- [ ] GitHub Actions最終PASS
- [ ] 独立QA
- [ ] PR merge
- [ ] main Pages deploy確認

最後の4項目を通過してA1.3完了とする。
