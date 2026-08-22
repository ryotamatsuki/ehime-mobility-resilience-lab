# A1.8 QA Report — Route / Trip Criticality

判定: **PASS WITH WARNING / merge可（最終head CI通過を条件）**

基準日: 2026-08-22

## 検証対象

- trip-level outage routing gate
- active route leave-one-out
- active trip leave-one-out
- outage monotonicity
- deterministic ranking
- A1.7 temporal profile回帰
- A1.6 walking transfer回帰
- A1.5 official hospital gate回帰
- Planning Canvas criticality card

## PASS

### 1. Trip-level outage

`earliest_arrival_minutes`へ`disabled_trips`を追加した。

synthetic unit testでは同一路線の先行便だけを停止した場合に、後続便へ切り替わり、route全体を停止せず便単位の欠便を正しく表現できることを確認した。

### 2. 実データ全件評価

2026-08-21のactive serviceについて:

- active routes: 4
- active trips: 11
- 4 routeすべてを単独停止して再計算
- 11 tripすべてを単独停止して再計算

### 3. Monotonicity

全1,840人口メッシュについて、route/tripを停止した結果がBaselineより早くなるケースがないことをビルド時に検証した。

### 4. Ranking

順位ルールは:

1. `population_with_gt_1min_increase` 降順
2. `mean_minutes_change` 降順
3. ID昇順

で固定し、CIで並び順を再検証する。

### 5. Top result

route 1位:

- route 21
- 市内循環バス(ぐるりんおおず)右回り・土日祝運休便
- 1分超悪化人口 1,955.2890人相当
- 平均所要時間悪化 +0.728分

trip 1位:

- `21+0+土日祝運休便+1`
- route 21
- 07:15発
- 市立大洲病院行
- 1分超悪化人口 1,955.2890人相当
- 平均所要時間悪化 +0.728分

### 6. Regression

- A1.7 06:00〜21:00 / 16時点 temporal profile保持
- A1.6 walking transfer 156 directed edges保持
- A1.5 verified hospital destinations 5施設保持
- official medical workbook未配信
- Planning CanvasへTemporal ResilienceとService Criticalityを併存表示

## Warning

### W1. 08:00断面のCriticality

Criticalityは08:00のleave-one-out結果であり、終日平均の重要度ではない。A1.7で時間帯感度が確認されているため、将来は時間帯別Criticalityへ拡張可能だが、本Stageでは分析定義を明確にするため08:00へ固定した。

### W2. 社会的重要度ではない

0人影響のroute/tripを「不要」と解釈してはならない。本指標は今回の病院Accessibilityという目的関数に対する感度のみを示す。実利用者数、通学・買物、運行費、代替車両、要配慮者重み等は含まない。

## Blocker

なし。最終head CI全PASS後にmerge可。
