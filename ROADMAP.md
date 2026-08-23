# Ehime Mobility Resilience Lab — Development Roadmap

更新日: 2026-08-24

基準 main SHA: `dfef5c04ac95541bc62db711e5279de92daf0845`

この文書は、`docs/SPECIFICATION.md` の長期構想を維持しつつ、公共交通オープンデータチャレンジ2026に向けた実装順序を明確化するための実行ロードマップである。

## 1. 現在地

A0 Foundation と A1 の公共交通レジリエンス分析は、A1.12 および A1.H まで完了している。

### 完了済み

- [x] A0 — Foundation / Data Feasibility / Architecture
- [x] A1.1 — Real GTFS + OSM + population / hospital accessibility
- [x] A1.2 — WebGIS demo
- [x] A1.3 — Planning Canvas
- [x] A1.4 — Mobile / responsive UI
- [x] A1.5 — Official hospital registry verification
- [x] A1.6 — Walking transfer model
- [x] A1.7 — Time-of-day accessibility analysis
- [x] A1.8 — Route / Trip Criticality
- [x] A1.9 — Emergency / general / welfare shelter accessibility
- [x] A1.10 — Destination Switcher
- [x] A1.11 — Time-dependent Criticality
- [x] A1.12 — Vulnerable Population / Equity Analysis
- [x] A1.H — Architecture / Technical-Debt Hardening

A1.H では、Golden regression、stage spoofing 除去、export contract 統合、Ruff、strict zip checks、process-local source cache 等を追加し、A1.12 のモデル値を変更せずに再現性と保守性を強化した。

## 2. 2026 Competition-first 優先ロードマップ

ここからは、機能数を増やすことよりも、審査員が短時間で確認できる「問題 → 発見 → 頑健性 → 対策 → 汎用性」を完成させることを優先する。

実装順序は次のとおりとする。

1. A1.13 Robustness / Uncertainty
2. A1.14 Real-world Evidence Anchor
3. A1.15 Recovery Scenario Lab
4. A1.16 Multi-feed / Multi-operator Validation
5. A5.C Competition Mode UI
6. A6.C Competition Release
7. その後、A2 / A3 / A4 の県域・道路・物流拡張へ進む

---

## 3. A1.13 — Robustness / Uncertainty

### 目的

A1.11 / A1.12 で得られた Critical Route / Trip、時間帯、年齢層別負担差が、特定のモデル仮定だけに依存した結論ではないことを検証する。

### 原則

- 新しい「Robustness Score」のようなブラックボックス合成指標は作らない。
- 各条件で結論が維持されたかをそのまま表示する。
- A1.12 Golden Baseline は変更しない。
- Sensitivity parameter の変更と、データ更新による drift を区別する。
- 全条件を機械的に評価し、都合のよい条件だけを選ばない。

### 感度分析候補

- 徒歩速度
- 徒歩アクセス上限
- 徒歩乗換距離
- 出発時刻 / 時間帯
- Accessibility threshold
- 人口グループ（all / 65+ / 75+ / 85+）
- 目的地集合（hospital / emergency / general / welfare）

### 期待する出力例

- 「12条件中11条件で同じ route が Top 3」
- 「85+ の影響率が全人口より高い方向は 12/12 条件で維持」
- 「徒歩速度 0.5 m/s の条件のみ順位が入れ替わる」
- 「結論が不安定になる境界条件」を明示

### Release Gate

- [ ] Sensitivity parameter と範囲を文書化
- [ ] 全条件を同一コードパスで再計算
- [ ] ベースライン A1.12 Golden PASS
- [ ] route / trip ranking stability を保存
- [ ] equity direction stability を保存
- [ ] 条件ごとの差分 provenance を保存
- [ ] UI では合成スコアを作らず条件別結果を説明可能に表示
- [ ] pytest / Ruff / source probe / generated-site smoke PASS

---

## 4. A1.14 — Real-world Evidence Anchor

### 目的

Stress Test の停止シナリオを、単なる仮定ではなく実在する交通・防災上の課題またはニーズへ接続する。

### Anchor 候補

最低1種類、可能なら複数を利用する。

- 過去の公共交通運休実績
- 過去の道路通行規制・災害途絶
- 災害時運行計画・地域防災計画
- 通院・高齢者移動ニーズを示す公式資料
- 自治体または公共交通事業者ヒアリング

### 成果物

`Reality Evidence Card` を作成し、少なくとも次を区別して表示する。

1. 実際に観測・確認された事実
2. そこから設定した Stress Test
3. モデルが計算した結果
4. モデルからは言えないこと

### Release Gate

- [ ] 1件以上の実在課題を一次資料または明示的ヒアリングで確認
- [ ] Evidence と D区分 scenario を混同しない
- [ ] 出典・日時・適用範囲を provenance に保存
- [ ] 「なぜこの Stress Test をするのか」を30秒で説明できる

---

## 5. A1.15 — Recovery Scenario Lab

### 目的

「止めると何が困るか」という診断から、「限られた資源で何を戻せば最も回復するか」という処方へ進む。

### 初期 Recovery 候補

- Critical Trip を1便維持
- 一部便を復旧
- 臨時便を追加
- 代替停留所へ接続
- 既存別 route への徒歩接続

### 主指標

- 回復人口
- Accessibility Loss の回復量
- 平均所要時間悪化の縮小
- 30 / 60分到達圏の回復
- 年齢層別回復量
- 追加1便または1施策あたりの回復効果

### 原則

- Recovery の「最適」を、費用・実現可能性を無視して断定しない。
- 運行可能性、車両・乗務員制約を未取得なら D 区分として明示する。
- 何もしない scenario を必ず比較基準に置く。

### Release Gate

- [ ] Baseline / Disruption / Recovery を同一指標で比較
- [ ] 少なくとも2つの Recovery option を比較
- [ ] 年齢層別 recovery を表示
- [ ] 施策前提を provenance に保存
- [ ] Competition story が「問題 → 発見 → 対策」までつながる

---

## 6. A1.16 — Multi-feed / Multi-operator Validation

### 目的

Ehime Mobility Resilience Lab が「ぐるりんおおず専用」ではなく、GTFS を使った汎用的な交通レジリエンス分析手法であることを実証する。

### 方針

- 愛媛県全域展開そのものを目的にしない。
- 大洲とネットワーク構造が異なる GTFS を最低1フィード追加する。
- 可能なら複数 route、乗換、複数 operator を含むケースを選ぶ。
- 同じ分析コードを使い、地域固有 hard-code を追加しない。

### 最低検証範囲

- GTFS ingest
- service date / 24時超時刻
- walking transfer
- Accessibility
- Route / Trip Criticality
- Time-dependent Criticality
- Robustness

### Release Gate

- [ ] 第2 GTFS を同一 pipeline で完走
- [ ] feed 固有 hard-code なし
- [ ] 主要 schema 差異への failure / fallback behavior を確認
- [ ] 第1・第2 feed の結果 provenance を分離
- [ ] 「GTFSなら他地域でも動く」ことを再現手順付きで示す

> 注: 開発初期に「A1.7 Multi-feed / Multi-route Validation」という仮称を使ったが、A1.7 はその後 Time-of-day analysis に使用したため、Multi-feed 検証は正式に A1.16 とする。

---

## 7. A5.C — Competition Mode UI

### 目的

通常の研究・行政向け Lab UI と、コンテスト審査向けの情報量を分離する。

### Competition Mode の最初の30秒

審査員が次の3点を理解できること。

1. 何が止まると問題なのか
2. 誰がどの程度困るのか
3. 何を戻すとどの程度回復するのか

### UI 方針

- 未実装・未実証の道路、鉄道、航路、港湾、物流機能は応募版トップ画面から隠す。
- 将来構想は後段の「拡張可能性」で説明する。
- 最重要発見を1件、最初に提示する。
- Robustness は条件維持率と不安定条件を簡潔に表示する。
- Evidence / Assumption / Model Result を明確に分ける。
- Provenance は残すが、初見の理解を妨げない階層に置く。

### Release Gate

- [ ] 30秒理解テスト
- [ ] 5分デモシナリオ固定
- [ ] 未実装UIを応募画面から除外
- [ ] mobile / desktop smoke
- [ ] Accessibility / keyboard / contrast 基本QA
- [ ] Public URL で全デモが再現可能

---

## 8. A6.C — Competition Release

### 目的

公共交通オープンデータチャレンジ2026提出版を固定する。

### 成果物

- Public WebGIS
- GitHub repository
- README / ROADMAP / methodology / provenance
- 作品説明文
- 利用マニュアル
- 代表的発見
- 5分デモ手順
- 必要に応じて説明動画・スライド

### Final Gate

- [ ] 代表的発見を30秒で説明可能
- [ ] Reality Anchor が一次資料で追跡可能
- [ ] Recovery Scenario が再現可能
- [ ] Multi-feed validation PASS
- [ ] Golden / Robustness / CI PASS
- [ ] raw data / license / attribution audit PASS
- [ ] Public Pages E2E PASS
- [ ] 応募画面に未完成機能が露出していない

---

## 9. 長期マスタープラン — Competition-first 後に再開

以下は廃止しない。`docs/SPECIFICATION.md` に定める行政PoC・県域展開の正式な長期構想として保持する。

### A2 — Synthetic OD

- 通勤・通学実績制約
- 市町内細粒度推計
- 非通勤目的 Gravity Model
- 県外流動制約
- 貨物ODは乗用車と分離

### A3 — Traffic Assignment / Road Resilience

- OSM road network
- alternative route
- BPR
- deterministic MSA approximation
- GEH / MAPE / RMSE / screenline / VKT
- road criticality / recovery priority

### A4 — Freight / Relief Logistics

- freight vehicle network
- ports / warehouses / industrial areas
- relief logistics nodes
- accessibility / isolation / alternative route
- 民間在庫や完全な企業間 supply chain は推定しない

### A5 — Operational UX

- non-engineer Data Update Center
- validation / diff / preview / approval / active switch
- reproducible scenario management

### A6 — Production / Administrative PoC

- 愛媛県域への段階展開
- 行政部門別 workflow
- production QA / operations / maintenance

---

## 10. Phase B — Official Hazard Scenario Adapter

Phase B は Competition-first roadmap と独立した optional adapter とする。

愛媛県新地震被害想定 GIS 等の利用条件について必要な許諾・確認が得られた場合のみ実装する。

許諾前に、加工済み hazard GIS、派生 GeoJSON、再分類済み危険度レイヤー等を公開しない。

Phase B が実装されなくても Phase A / Competition Release は完成品として成立しなければならない。

---

## 11. 開発判断ルール

今後の Stage 追加は、次の順で評価する。

1. 審査員または行政利用者の具体的な意思決定を改善するか
2. 既存分析の信頼性・実証性を高めるか
3. 代表的発見を明確にするか
4. 既存機能で代替できないか
5. 技術的面白さだけを理由にしていないか

Competition Release までは、A2/A3/A4 の大規模実装より A1.13〜A1.16 を優先する。

## 12. 現在の次アクション

**NEXT: A1.13 Robustness / Uncertainty**

最初に Sensitivity parameter、base condition、評価対象 conclusion、出力 contract、Golden 非変更条件を固定し、その後に実装へ入る。
