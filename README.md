# Ehime Mobility Resilience Lab

「もし、ここが通れなくなったら。」

公共交通・道路・物流を構成する交通ネットワークを平時に意図的にストレステストし、愛媛県内の人・車・物の移動への影響を説明可能な形で検証する、GitHub Pages公開型のWebGISとPython分析基盤です。

## Single Source of Truth

開発の正式仕様は、次の文書です。

- [開発仕様書 Version 1.0](docs/SPECIFICATION.md)

Phase Aは愛媛県新地震被害想定GISに依存しません。公式値・加工値・モデル推計値・ユーザー仮定を区別し、結果には使用データ・モデル・パラメータ・生成日時を付与します。

## Status

実装状況は、仕様書・決定記録・各検証文書に基づき更新します。

## デモ

公開層は web ディレクトリからGitHub Pagesへ配信します。初期版では、実取得済みのOSM主要道路、R3道路交通センサス、R6 500m人口メッシュを使った道路Stress Testを表示します。GTFS、県内詳細OD、物流・救援拠点データは、取得条件が確定するまで画面上で外部入力または未計算と表示します。

画面の基本操作は、平常時を見る → 止めてみる → 何が困る？ → どう戻す？ → どこが重要？です。任意の道路を選択できますが、Pages上で重い再計算を実行せず、未計算状態を明示します。

## インストールと実行

必要条件はPython 3.12以上です。依存を最小化した標準ライブラリ中心の解析層と、静的JavaScriptのPublic Layerで構成します。

    python -m venv .venv
    . .venv/bin/activate
    PYTHONPATH=src python -m unittest discover -s tests -v
    python -m http.server 8000 --directory web

公開用データを再生成する場合は、DATA_INVENTORY.mdとDATA_LICENSES.mdを確認したうえで、ローカルに取得した入力を使います。

    PYTHONPATH=src python scripts/build_network/build_public.py
    python scripts/validate/run_validation.py

取得済み原データがない環境では、既存のweb/dataを使い、原データの不存在をゼロ値として補完しません。

## モデル概要

- GTFS：stops、routes、trips、stop_times、calendar、calendar_datesを解釈し、service dateと24時超の時刻を扱います。
- 道路：OSM主要道路を有向グラフ化し、完全停止、容量低下、速度低下をScenarioとして保存します。
- Synthetic OD：通勤・通学、市町村間制約、非通勤、貨物を分離し、IPFとGravity Modelを使います。モデル値はC区分です。
- Traffic Assignment：BPRと決定論的MSA近似で静的配分を行い、GEH、MAPE、RMSE、screenline、VKTを保存します。
- Accessibility：30分、60分、90分圏、到達可能人口、Accessibility Lossを算出します。
- Logistics / Relief：公開条件と位置が確認できたノードだけを使います。在庫量や企業間サプライチェーンを推定しません。

## データ更新

管理者環境でData Update Centerを起動できます。

    PYTHONPATH=src python admin/app.py --root . --port 8765

アップロード → 形式確認 → 自動Validation → 旧版との差分 → プレビュー → 承認 → active切替の順で処理し、直接上書きと失敗版のactive化を禁止します。詳細は [OPERATIONS.md](docs/OPERATIONS.md) を参照してください。

## データ区分とライセンス

Aは公式観測・実績、Bは公式統計加工、Cはモデル推計、Dはユーザー仮定です。各結果の区分と出典を画面のProvenanceで確認できます。

コードはMIT Licenseです。OSMはODbL 1.0、人口メッシュは掲載条件に従うCC BY 4.0、道路交通センサスとe-Stat・愛媛県オープンデータは各個別条件に従います。ODPT GTFSの生データは規約確認前にリポジトリへ含めません。詳細は [DATA_LICENSES.md](docs/DATA_LICENSES.md) と [DATA_INVENTORY.md](docs/DATA_INVENTORY.md) を参照してください。

## 制約

このプロダクトは南海トラフや地震の発生・被害を予測しません。実被害予測、リアルタイム災害対応指示、個人移動履歴、民間在庫、完全な企業間サプライチェーン、未確認GTFSの補完は対象外です。

県内詳細自動車OD、交通量配分、GTFSアクセシビリティ、貨物・救援物流の実データ結果は、入力の取得と利用許諾が確定した範囲から段階的に有効化します。未計算をゼロ影響や実績値として表示しません。

## ドキュメント

- [Architecture](docs/ARCHITECTURE.md)
- [Data Availability Matrix](docs/DATA_AVAILABILITY_MATRIX.md)
- [Model Method](docs/MODEL_METHOD.md)
- [Synthetic OD Design](docs/OD_DESIGN.md)
- [Transit Feasibility](docs/TRANSIT_FEASIBILITY.md)
- [UX Design](docs/UX_DESIGN.md)
- [Validation](docs/VALIDATION.md)
- [Operations](docs/OPERATIONS.md)
- [Risk Register](docs/RISK_REGISTER.md)
- [A0 QA Report](docs/A0_QA_REPORT.md)
- [Phase B License Gate](docs/PHASE_B_LICENSE_GATE.md)
- [Competition Summary](docs/COMPETITION_SUMMARY.md)
- [Decisions Log](docs/DECISIONS.md)
