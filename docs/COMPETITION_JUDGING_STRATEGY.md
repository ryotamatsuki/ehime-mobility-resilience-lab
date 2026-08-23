# Competition Judging Strategy

## Document status

- Purpose: 公共交通オープンデータチャレンジ2026に向けた開発優先順位・審査上の強み・弱み・判断原則を固定する
- Status: Active / Single Source of Truth for competition strategy
- Scope: Competition-first roadmap、審査員視点、Competition Gate、応募時のストーリー設計
- Last reviewed: 2026-08-24
- Reference main SHA at review start: `2ab18cc43c1b79fb0c67c04e106b55e95939f0de`
- Competition: 公共交通オープンデータチャレンジ2026

この文書を Competition Strategy の Single Source of Truth とする。

`docs/COMPETITION_SUMMARY.md` は外向けの作品説明、`ROADMAP.md` は実装順序、`AGENTS.md` はLLM・開発者向けの恒常ルールを担う。審査戦略の根拠・優先順位・内部評価は本書で管理する。

> Important: 審査員本人の発言・公式審査基準と、本プロジェクト側の推論・戦略判断を混同しない。Verified facts / remarks と Project interpretation を明確に分離する。

## 1. Official competition context

### 1.1 募集の方向性

2026年の公式開催概要では、公共交通オープンデータを活用した新しいアプリケーション・サービスに加え、様々なデータを最大限に活用した地方での課題解決や新しいデータ利活用を募集している。また、ほこナビ、Project LINKS、Project PLATEAU等との組合せも強く推奨されている。

Source: https://challenge2026.odpt.org/ja/outline.html

### 1.2 公式審査基準

公式に明示されている主要審査観点は以下の4点である。

- 社会課題解決への寄与
- オープンデータ活用におけるインパクト
- 技術的な完成度
- UI / UX面の完成度

公式配点は公表されていない。以下の内部スコアは公式採点ではない。

## 2. Current internal competition readiness

**Internal heuristic only.**

| Axis | Internal score | Current interpretation |
| --- | ---: | --- |
| Social problem relevance | 18 / 25 | テーマは強いが、現実の課題・実需へのAnchorをさらに強める必要がある |
| Open-data impact | 21 / 25 | GTFSをAccessibility / Criticality / Equityへ展開している点が強い |
| Technical completeness | 24 / 25 | A1.Hまでの再現性・検証・CIは受賞候補水準 |
| UI / UX | 19 / 25 | Planning Canvasは強いが、未実装の将来機能が応募時に未完成感を与える可能性がある |
| **Total** | **approximately 82 / 100** | **Internal heuristic only** |

この評価は、テーマ変更が必要という意味ではない。現時点でも入賞候補となり得るが、最優秀賞候補として比較されるには「現実の課題 → 発見 → 頑健性 → 対策」の実証をもう一段完成させる必要がある。

## 3. Core strategic position

### 3.1 Theme

テーマそのものは弱くない。

公共交通 × 地方課題 × 防災・レジリエンス × 高齢化 × 医療・避難アクセス × オープンデータという組合せは、2026チャレンジの趣旨との整合性が高い。

**原則としてテーマ変更はしない。**

### 3.2 GTFS utilization as differentiation

GTFSを単なる時刻表、運行表示、経路検索に使わず、以下へ展開している点を主要な独自性とする。

- time-dependent accessibility
- route / trip leave-one-out criticality
- temporal resilience
- destination accessibility
- vulnerable population / equity

今後はさらに、Robustness、Reality Anchor、Recoveryへつなげることで「公共交通ネットワークの反実仮想Stress Test」という一貫した価値にする。

### 3.3 Analytical truthfulness

以下は本プロジェクトの主要な信頼性資産であり、今後も維持する。

- A / B / C / D provenance区分
- 観測・加工・モデル・仮定の分離
- 未計算をゼロ扱いしない
- 年齢を要配慮者そのものと扱わない
- Equityを因果効果と主張しない
- 合成Vulnerability scoreを安易に作らない
- Golden regression
- actual-data CI
- source probe
- generated-site smoke
- raw source publication exclusion

### 3.4 Technical maturity

A1.Hまでに以下が実装されている。

- Golden regression
- Ruff
- stage spoofing除去
- exporter contract統合
- strict mismatch detection
- exact-request process cache
- CI / Pages separation

ただし、これらは主として**減点を防ぐ技術品質**である。

**CI、Golden regression、Provenance、静的解析は必要条件だが、それ自体をコンペの主要な受賞理由と考えない。**

技術的高度化そのものを目的化してはならない。

## 4. Main competition blockers

### P0 — Real-world problem anchor

現状の「右回り運休」はD区分Stress Testとして科学的には適切である一方、次の問いへの現実側の根拠が弱い。

> なぜその route / trip を止めて検証するのか。

今後、最低1つを実在する証拠へ接続する。

- 実際の公共交通運休
- 道路規制・災害途絶
- 災害時の運行制約
- 自治体・交通事業者の課題認識
- 医療アクセス上の実需
- 過去災害事例
- 明示的なヒアリング

目標は「分析したいから止めた」から「現実に起こり得る、または実務上確認したいのでStress Testした」へ移行することである。

### P0 — Diagnosis to Recovery

現状は「止めると何が困るか」の診断能力が強い。

次の主要価値は、

> 何を戻せば、どれだけ回復するか。

を比較可能にすることである。

候補:

- 特定便を維持
- 一部routeを復旧
- 臨時便
- 代替接続
- 仮設アクセス

`Recovery per intervention` を説明できる方向を優先する。ただし、費用・車両・乗務員等を観測していない場合は「最適」と断定しない。

### P1 — Robustness / Uncertainty

A1.11 Criticality / A1.12 Equityの主要結論が、特定の単一パラメータだけで成立していないか確認する。

候補:

- 徒歩速度
- 出発時刻
- transfer条件
- destination設定
- population条件
- time sampling

目的は感度分析そのものではなく、審査員に次を説明可能にすることである。

> この結論は特定の1条件だけで出た偶然ではない。

ブラックボックスな合成Robustness scoreは作らない。代わりに、

- 何条件中何条件で結論が維持されたか
- どの条件でランキングが変わるか
- どの結論が不安定か

を透明に示す。

### P1 — Representative findings

現在は分析項目が豊富だが、審査員が短時間で覚える代表的発見が弱い。

応募時は1〜3個に絞る。

現時点で候補となる実データ由来の発見例:

- 08:00固定では最大影響時刻を見逃す
- Critical route / trip は時間帯によって変わる
- 病院アクセスでは今回の100m人口分布上、年齢層が上がるほど1分超悪化率・平均悪化時間が大きい傾向がある

最終表現は必ずその時点の実データで再検証する。分析結果以上の一般化、因果主張、誇張をしない。

### P1 — Competition Mode UI

Planning Canvasには道路、鉄道、航路、港湾等の将来Stageが含まれており、開発UIとしては有用だが応募版では未完成感につながる可能性がある。

応募時は以下を優先する。

- 実装済み
- 検証済み
- 実データで再現可能

な機能を前面に出す。

未実装機能は原則として応募版トップ画面から隠すか、明確なRoadmapへ退避する。

### P2 — Multi-feed / Generalization

大洲の1feed専用ではなく、別GTFSでも同じ分析pipelineが動くことを確認する。

ただしP0/P1より優先しない。県全域展開や対応feed数そのものを目的化しない。

## 5. Judge-specific lenses

2026年の審査員構成は公式開催概要で確認する。

Official source: https://challenge2026.odpt.org/ja/outline.html

過去講評を参照する場合:

- 2025 comments: https://challenge2025.odpt.org/award/remarks.html
- 2024 awards / comments: https://challenge2024.odpt.org/award/

### 5.1 坂村 健

#### Verified background / remarks

- 2026審査員長。公共交通オープンデータ協議会会長、東京大学名誉教授、INIAD cHUB機構長。
- 2024講評では、最優秀賞「急がば漕げマップ」について、明確な課題設定と複数オープンデータの組合せを高く評価した。
- 2024講評ではGTFS boxの高品質なGTFSビューアとオープンソース公開にも言及した。

#### Implication for this product

Project interpretation:

「交通が止まった愛媛を事前に何度も試す」という課題設定は相性が良い。一方、分析項目の多さよりも「この分析で新しく何が分かったか」を一発で理解できることが重要と考える。

#### Recommended action

- Representative Findingを1〜3件へ絞る
- 30秒で「課題 → 発見」を説明できる形へする
- 複数データの組合せが何を可能にしたか明示する

### 5.2 渡邉 明博

#### Verified background / remarks

- 2026審査員。
- 国土交通省 総合政策局 モビリティサービス推進課 総括課長補佐。
- 公式プロフィールでは航空、防災、不動産など幅広い政策分野に従事してきたとされる。
- 本プロジェクト執筆時点で、2026チャレンジに関する本人の具体的な審査講評はまだ存在しない。

#### Implication for this product

Project interpretation:

政策・行政実装の観点では、「分析を見て自治体・事業者が何を変えられるのか」が重要な評価ポイントになり得る。

#### Recommended action

- CriticalityをRecovery / Intervention Comparisonへ接続する
- どの便を維持するか、何を復旧するか、どこへ代替輸送を投入するかという意思決定へ落とす
- モデル結果と政策推奨を混同しない

### 5.3 Tzu-Jen Chan

#### Verified background / remarks

- 2026審査員。GTFS Program Manager, MobilityData。
- 2025講評では、MobivizとTraffic EchoがGTFS-Flexを経路検索だけでなく交通計画の視点から活用し、交通空白の課題解決を示した点を評価している。
- 2025講評では複数データを組み合わせることで生まれる新しい価値にも言及している。

#### Implication for this product

Project interpretation:

GTFSをAccessibility / Criticality / Equityへ使う方向との相性は良い。次の問いは「大洲の特殊事例か、GTFS一般に適用できるか」となる可能性が高い。

#### Recommended action

- P0/P1完了後に別feedでGeneralizationを実証する
- feed固有hard-codeを避ける
- GTFS標準を使うことで他地域へ再利用可能な分析手法であることを示す

### 5.4 山口 智丈

#### Verified background / remarks

- 2026審査員。JR東日本でデータ活用・サービス開発等に従事。
- 2025講評では、受賞作品が向き合う課題・ニーズについて「単なる仮説や思い込みではなく、現実の場で実証された本物」であることを重視する趣旨を明確に述べている。

#### Implication for this product

Project interpretation:

現状の最大リスクの1つ。「右回り運休」が科学的に透明なD区分Stress Testであっても、「なぜ右回りを止めるのか」というReality Anchorが弱いままでは評価を落とし得る。

#### Recommended action

- Real-world Evidence AnchorをP0として扱う
- 実際の運休・道路規制・政策資料・利用者ニーズ・ヒアリング等と接続する
- Evidence、Assumption、Model Resultを分離して表示する

### 5.5 草薙 昭彦

#### Verified background / remarks

- 2026審査員。Postman株式会社テクノロジーエバンジェリスト、Mapbox Japanアンバサダー。
- デジタルツイン・データビジュアライゼーションに関心を持ち、Mini Tokyo 3D、PIEN、GTFS boxなど複数の受賞歴が公式プロフィールに記載されている。
- 本プロジェクト執筆時点で、2026チャレンジに関する本人の審査講評はまだ存在しない。

#### Implication for this product

Project interpretation:

公共交通Webアプリ・可視化として、一目で理解できること、操作の明快さ、完成品としての密度が重要になり得る。未実装の将来機能が多数見えることは不利になり得る。

#### Recommended action

- Competition Mode UIを用意する
- 「問題 → 発見 → 対策」を短時間で理解できる構成にする
- 未実装・未実証機能を応募トップから除外する

### 5.6 別所 正博

#### Verified background / remarks

- 2026審査員。INIAD教授。
- 公式プロフィールでは、IoT・AIによる社会課題解決、歩行者ナビゲーション、障がい者支援、オープンデータ、混雑検出等を研究領域としている。
- 本プロジェクト執筆時点で、2026チャレンジに関する本人の審査講評はまだ存在しない。

#### Implication for this product

Project interpretation:

A1.12 Equityは重要な加点要素になり得る。ただし、年齢区分を障害・要介護・医療的ケア等まで代表するものとして扱うと、現在の分析上の誠実さを損なう。

#### Recommended action

- 65+ / 75+ / 85+を「要配慮者そのもの」と同一視しない方針を維持する
- 利用可能な公開データがない属性を無理に推計しない
- 将来、信頼できる移動制約・歩行空間データが得られる場合のみ段階的に拡張する

## 6. Development decision principles

以下を今後の上位判断原則とする。

1. テーマ変更はしない。
2. 技術的完成度だけを際限なく磨かない。
3. CIやGolden regressionは必要だが、それ自体を受賞理由とは考えない。
4. 大洲1地域の実証を完成させる前に県全域へ広げすぎない。
5. 「右回りを止めたらどうなるか」から「なぜ検証するのか」へ進める。
6. Criticality → Robustness → Real-world Anchor → Recoveryを主要な流れとする。
7. 代表的発見を1〜3個へ絞る。
8. 未実装の大構想を応募UIで前面に出さない。
9. 分析の不確実性・限界を隠さない。
10. 数字を大きく見せるために結果を誇張しない。
11. 実データとモデル値を混同しない。
12. 新機能は「審査上の弱点を改善するか」を確認してから追加する。

## 7. Grand Prize Candidate Gate

これは公式要件ではなく、内部Competition Readiness Gateである。全項目を機械的に必須条件と断定しないが、未充足項目は応募前に明示的にレビューする。

- [ ] Critical route / tripの主要結論についてRobustnessを説明できる
- [ ] 少なくとも1つの現実の課題・運休・政策ニーズにAnchorされている
- [ ] DiagnosisだけでなくRecovery / Intervention比較ができる
- [ ] 代表的な1〜3個の発見を30秒で説明できる
- [ ] 応募版UIに未完成感がない
- [ ] GTFS活用の新規性を簡潔に説明できる
- [x] データ・モデル・仮定のProvenanceを追跡できる
- [x] 実データQA / regression / generated-site smokeをRelease Gateとして持つ

チェック済み項目も、応募時の最終mainで再検証する。

## 8. Competition-first sequence

現在の推奨順序:

1. A1.13 — Robustness / Uncertainty
2. A1.14 — Real-world Evidence Anchor
3. A1.15 — Recovery Scenario Lab
4. Representative Finding consolidation
5. Competition Mode UI
6. A1.16 — Multi-feed / Multi-operator Validation
7. Competition Release

`ROADMAP.md` の正式Stage番号とRelease Gateを優先する。将来ロードマップが明示的なレビューで変更された場合、本書も同時に更新する。

## 9. Stage Competition Gate

新Stageの提案時と終了時に、最低限以下へ回答する。

- Which judging weakness does this stage address?
- Does it improve a P0 / P1 / P2 competition blocker?
- What new evidence does it provide?
- What can now be explained to a judge that could not be explained before?
- Does it introduce unfinished UI or unnecessary scope?
- Does it preserve analytical truthfulness?

これらに具体的に回答できない新機能は、原則としてCompetition Release前の優先順位を下げる。

## 10. Anti-patterns

Competition Release前は以下を避ける。

- 技術的に面白いという理由だけの新分析
- 実在課題への接続より先に県全域へ広げる
- 未取得データを推定で埋めて見かけ上の完成度を上げる
- 「高齢者＝要配慮者」と短絡する
- A1.12 Golden値を新しい結果に合わせるだけの更新
- 未実装機能を応募トップ画面に大量に置く
- 合成スコアで不確実性を隠す
- 平均値だけを見せて分布や例外を隠す
- 実証されていない政策効果を断定する
- CIやリファクタリングを作品ストーリーの中心にする

## 11. Updating this strategy

次の場合は本書を更新する。

- 公式審査基準・審査員が変更された
- 新しい公式審査講評が公開された
- P0/P1 blockerが実証により解消された
- Competition-first roadmapの優先順位を変更した
- 代表的発見が正式に固定された
- Competition Mode UIが完成した

更新時も Verified background / remarks と Project interpretation の分離を維持する。
