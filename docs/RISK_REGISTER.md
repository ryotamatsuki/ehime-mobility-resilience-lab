# A0 Risk Register

調査基準日：2026年8月22日（JST）

| Risk | Probability | Impact | Mitigation | Owner | Status |
|---|---:|---:|---|---|---|
| 県内全域をカバーするGTFSがない | High | Critical | 事業者別coverageを表示し、未確認路線を補完しない | Transit / PM | Open |
| ODPT GTFSの個別規約・認証が未確認 | Medium | Critical | 生ZIPをcommitせず、external_inputで管理 | Licensing | Open |
| 鉄道GTFSが未確認 | High | High | N02等の形状を時刻表と混同せず、未計算表示 | Transit | Open |
| 県内詳細自動車ODが公開されていない | High | Critical | 市町村OD・広域OD・メッシュ分布を制約とするSynthetic設計 | OD | Open |
| Synthetic ODが非一意 | High | High | Seed/IPF、holdout、感度分析、C区分表示 | OD / QA | Open |
| 道路容量の既定値が仮定 | High | High | lanes、maxspeed、センサスを分離し、既定値をDまたはCとして保存 | Road | Open |
| OSM主要道路縮約が全道路と誤認される | Medium | High | public bundleの注記、対象道路種別、抽出日時を表示 | GIS | Mitigated |
| R3交通センサスとOSMリンク対応の誤差 | High | High | 対応方法、観測・非観測、方向、時間帯を固定し検証 | Traffic / QA | Open |
| 貨物統計から企業在庫を誤って推計 | Medium | Critical | 在庫・企業間サプライチェーンを対象外とし、施設アクセスに限定 | Freight | Mitigated |
| 救援拠点の現行性・座標が不確実 | High | High | 公式版、更新日、座標根拠、数量の有無を別管理 | Relief | Open |
| Phase B GISの加工・派生が混入 | Low | Critical | Gate文書、blocked metadata、CI boundary check | PM / Licensing | Mitigated |
| GitHub Pagesで重計算をしようとする | Medium | Critical | 静的bundleとAnalysis Layerを分離し、not_computed状態を用意 | Architecture | Mitigated |
| PagesへAdmin機能や秘密情報が露出 | Low | Critical | Adminを別実行環境にし、公開bundleを静的検査 | Operations | Open |
| ZIP Slip、Zip Bomb、巨大アップロード | Medium | Critical | 展開前検査、member数・サイズ・パス制限、candidate隔離 | Operations | Open |
| 年次データ混在による時点誤認 | High | High | reference_date、imported_at、基準年を全結果へ付与 | Data | Open |
| モデルconfidenceの過剰表現 | Medium | High | 根拠付きカテゴリのみ、確率表現を避ける | QA / UX | Mitigated |
| OSM派生物のライセンス互換性 | Medium | Critical | attribution、ODbL、混合データの公開形態を監査 | Licensing | Open |
| GitHub履歴とPagesサイズの増大 | Medium | Medium | rawデータをcommitせず、縮約public bundleとchecksumを保存 | Architecture | Mitigated |
| 非エンジニア運用が属人化 | Medium | High | candidate→validated→active→archivedと日本語エラー表示 | Operations | Open |
| A1実装をA0で過剰に進める | Medium | High | Stage Gate、停止条件、今回のA0 QA報告で凍結 | PM | Mitigated |

## Release blocker

CriticalのOpenリスクは、A1以降の実データ投入前に、入力版・ライセンス・データ範囲・計算状態を確定する。未解決のまま実績値や実被害を表示しない。
