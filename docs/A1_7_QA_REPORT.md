# A1.7 QA Report — Ozu Temporal Resilience

判定: **PASS WITH WARNING / merge可（最終head CI通過を条件）**

基準日: 2026-08-22

## 検証対象

- 06:00〜21:00の16時点再計算
- Baseline / 右回り運休の同一入力比較
- A1.6 walking transfer回帰
- A1.5 official hospital gate回帰
- 08:00地図断面の互換性
- temporal_profile.json公開契約
- Planning Canvasへの時間帯サマリー表示

## 実データ結果

- GTFS stops: 37 / 37 snapped
- temporal slots: 16
- verified hospital destinations: 5
- walking transfer edges: 156
- population zones: 1,840
- population: 26,553.4167人相当

### 最大影響時刻

11:00

- 1分超悪化人口: 3,370.5401人相当
- 人口加重平均所要時間悪化: +0.895分

### 最小影響時刻

06:00

- 1分超悪化人口: 0人相当

### 従来基準時刻 08:00

- 1分超悪化人口: 2,030.3675人相当
- 5分超悪化人口: 1,610.0595人相当
- 10分超悪化人口: 1,203.3898人相当
- 平均所要時間悪化: +0.732分
- 30分到達圏損失: 0
- 60分到達圏損失: 0

08:00固定だけでは最大影響時刻を捉えられないことを確認した。

## QA Gate

各時点で以下を検証する。

- Baselineの30分到達人口 >= Scenario A
- Baselineの60分到達人口 >= Scenario A
- 16時点が06:00〜21:00に欠損なく存在
- raw official medical workbookを公開しない
- 公開病院は公式台帳照合済みOSM featureのみ
- temporal_profile.jsonは派生C区分成果物として公開

## Warning

### W1. 1時間刻み

終日傾向を小さなStageで安定して検証するため60分刻みとした。11:00が最大という結果は、この16サンプル内での最大であり、例えば10:30や11:30がさらに大きい可能性は否定しない。

### W2. 実被害予測ではない

右回り運休はD区分のStress Testであり、災害時に実際に当該routeが停止する確率や被災箇所を予測したものではない。

## Blocker

なし。最終headのCI全PASS後にmerge可。
