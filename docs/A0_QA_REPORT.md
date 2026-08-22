# A0 QA / Red-Team Report

## 判定

A0文書・構成・データ実現可能性の受入判定：PASS WITH WARNINGS

今回のStage Gateでは、新たなA1実装を進めず、作成済みの成果物を含めてA0の基盤として確認した。既に作成されている道路グラフ、GTFS parser、OD、交通配分、WebGIS、更新センター、fixtureは、ユーザー指示により成果物へ含めるが、A0完了判定では本県全域のモデル完成・精度検証済みとは扱わない。

## 確認済み

| Check | Result | Evidence |
|---|---|---|
| GitHub repository | PASS | ryotamatsuki/ehime-mobility-resilience-lab |
| 作業ブランチ | PASS | feature/a0-foundation-data-architecture |
| 仕様書 | PASS | docs/SPECIFICATION.mdを初回保存済み |
| Data Inventory | PASS | docs/DATA_INVENTORY.md |
| Availability Matrix | PASS | docs/DATA_AVAILABILITY_MATRIX.md |
| License audit | PASS WITH CONDITIONS | docs/DATA_LICENSES.md |
| Architecture | PASS | docs/ARCHITECTURE.md |
| OD design | PASS | docs/OD_DESIGN.md |
| Transit feasibility | PASS | docs/TRANSIT_FEASIBILITY.md |
| UX design | PASS | docs/UX_DESIGN.md |
| Phase B gate | PASS | blocked状態と禁止事項を記録 |
| Risk register | PASS | docs/RISK_REGISTER.md |
| Decisions log | PASS | docs/DECISIONS.md |
| CI skeleton | PASS | .github/workflows/ci.yml |
| Phase B data | PASS | 原データ・派生データをrepositoryへ投入していない |
| Local unit tests | PASS | 9 tests passed in the created fixture suite |
| Public bundle contract | PASS | JSON existence/type/smoke checks passed locally |
| Upload security fixture | PASS | ZIP path traversal rejection fixture passed |

## 独立レビューの反映

- Repository / Architecture：静的Pages、Python Analysis、管理環境を分離する方針を採用。
- Data / Licensing：GTFS、港湾、倉庫、現行施設一覧を条件付きまたは未確認として扱った。
- OD：通勤・通学者、乗用車、非通勤、貨物を分離し、市町村間総量を固定する設計にした。
- Transit：伊予鉄バス、公共GTFS候補、フェリー、鉄道のcoverageを混同しない記述にした。
- QA / Red Team：実被害予測、被害人口、実測交通量予測、根拠のないconfidenceの表現を避けた。

## Warnings

1. GitHub Actions PR #1 の最新run #7はPython・WebともにPASSした。Pages deployはmain限定ガードによりSKIPであり、Draft PRからは公開されない。A0ではmainを変更していないため、GitHub Pagesの公開URLは未発行・未確認である。
2. 国勢調査市町村OD、経済センサス、物流センサス、現行の救援施設位置は、A0の設計入力として確認したが、公開bundleの計算入力としては未取得または未確定である。
3. 先行して作成したA1相当コードを含むため、A0の作業コピーには準備的な実装が存在する。ただし、本報告後にA1の機能追加は行わず、次Stageの開始条件として凍結する。
4. R3道路交通センサスの取得ファイル、OSM原JSON、人口mesh ZIPはローカル再現用であり、公開リポジトリへ生データを無条件にcommitしない。
5. 実データの交通量Calibration／Validation結果は、対応リンクとOD入力が確定していないため未算出である。

## A0 Release Gate

- [x] repositoryが存在
- [x] 仕様書が保存済み
- [x] Data Inventory
- [x] Data Availability Matrix
- [x] Data Licenses
- [x] Architecture
- [x] OD Design
- [x] Transit Feasibility
- [x] UX Design
- [x] Phase B License Gate
- [x] Risk Register
- [x] Decisions Log
- [x] A0 QA Report
- [x] repository skeleton
- [x] CI skeleton
- [x] Phase Bデータなし
- [x] ライセンス不明の原データを公開bundleへ入れていない
- [x] A1開始条件を文書化

## A1開始時の最初の優先順位

1. 利用条件を確認したGTFS staticを一つ固定し、GTFS validationとfeed provenanceを実行する。
2. OSM主要道路縮約の対象範囲、道路属性既定値、センサス対応方法を確定する。
3. 人口・施設・目的地候補と基準日を固定し、最小のAccessibility fixtureを実データで実行する。
4. その後にSynthetic ODを、観測市町村ODと区分Cの細粒度分解として実装する。

この報告をもってA0で停止し、A1実装は次のユーザー指示を待つ。

## GitHub確認記録

- Repository: `https://github.com/ryotamatsuki/ehime-mobility-resilience-lab`
- Pull Request: `#1`、Draft、open、未merge
- main: A0開始時から未変更
- PR Actions: run #7、Python PASS、Web PASS、Deploy SKIPPED（main限定）
- GitHub Pages: A0では公開未実施。main統合後のRelease手順で確認する
