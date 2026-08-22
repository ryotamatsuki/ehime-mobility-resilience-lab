# Decisions Log

## ADR-0001: 仕様書と作業ブランチ

- issue: 既存ワークスペースの.gitへ書込みできない
- current specification: 仕様書を最初に保存し、作業ブランチで安全に進める
- technical problem: 既存作業を上書きせず、GitHubへ継続的に保存する必要がある
- options: 読み取り専用の既存Gitを変更する、別の作業コピーを使う、作業を停止する
- recommended option: /workspace/ehime-mobility-resilience-lab にGit作業コピーを作り、指定feature branchで管理する
- impact: GitHubのmainは変更せず、明示的な統合までfeature branchで進める
- decision: 採用

## ADR-0002: Static-first public layer

- issue: GitHub Pagesで高負荷な解析を実行できない
- current specification: 重い処理はPythonで実施し、公開層は事前計算結果を表示する
- technical problem: 大規模なブラウザ計算と認証情報を公開層へ置けない
- options: ブラウザで全計算、外部有料API、Pythonの事前計算成果物
- recommended option: 静的JSON・GeoJSONと軽量なScenario操作を利用する
- impact: 任意の組合せの再計算は分析層で実行し、未計算状態をUIで明示する
- decision: 採用

## ADR-0003: Paid map APIを必須にしない

- issue: 公開アプリの基本機能を有料APIに依存させない
- current specification: 有料APIなしで動作する
- technical problem: キー管理と費用が公開PoCの再現性を下げる
- options: 有料タイル、公開タイル、地図なし
- recommended option: 公開タイルまたは切替可能な静的背景とOSM attribution
- impact: 高負荷時のタイル制限は利用規約に従う
- decision: 採用

## ADR-0004: Restricted GTFSを公開bundleに含めない

- issue: ODPTの個別規約と認証条件をリポジトリ内で確定できていない
- current specification: ライセンス不明データを公開しない
- technical problem: 生ZIPや復元可能な派生を無条件に再配布できない
- options: 未確認のままcommit、外部入力として扱う、公共ライセンスの確認済みfeedだけ使う
- recommended option: 外部入力メタデータとfixtureで実装を検証し、規約確認後にfeed versionを登録する
- impact: 公開demoはGTFS未取得状態を明示し、Transitの計算可能性を隠さない
- decision: 採用

## ADR-0005: OSM主要道路の公開縮約

- issue: 原OSMスナップショットをそのまま公開すると容量と更新負荷が大きい
- current specification: OSMを道路ネットワークに使い、出典と再現性を保持する
- technical problem: Pages初期表示とリポジトリ容量
- options: 原データ全量、主要道路縮約、OSMを使わない
- recommended option: 抽出クエリを固定し、主要道路の公開GeoJSONを生成する
- impact: Phase Aの公開demoは主要道路のStress Testに限定し、全道路網でないことを表示する
- decision: 採用

## ADR-0006: Phase Bは許諾前に実装しない

- issue: 愛媛県新地震被害想定GISの改変・再配布条件が未許諾
- current specification: Phase B License Gate PASS後のみ
- technical problem: CC BY-NC-ND条件と公開派生物の衝突
- options: 加工して試す、原データを公開しない加工を行う、Adapter契約だけ設計する
- recommended option: Gate文書と空の境界だけを作り、データと処理を追加しない
- impact: Phase Aはユーザー仮定によるStress Testとして成立させる
- decision: 採用

## ADR-0007: Synthetic ODは推計値として分離する

- issue: 県内詳細自動車ODの公開確認ができない
- current specification: 市町間の観測総量を維持し、細粒度を推計する
- technical problem: 人の通勤OD、車両OD、貨物ODの混同リスク
- options: 詳細ODを公式値として扱う、推計層を分離する、OD機能を削除する
- recommended option: 目的・車種別のseedとIPFを分離し、C区分と明示する
- impact: 絶対予測ではなく相対的なネットワークStress Testとして評価する
- decision: 採用

## ADR-0008: Deterministic core

- issue: 同じ入力から同じ結果を再現する必要がある
- current specification: provenanceと再現性を必須とする
- technical problem: 乱数・順序依存・更新差分
- options: 乱数を許容、固定seed、完全決定論的な初期版
- recommended option: ID順序と固定seedを明示し、標準ライブラリ中心で決定論的処理を行う
- impact: 実データ精度の前に再現性を検証できる
- decision: 採用

## ADR-0009: Stage Gate

- issue: 大規模開発をA0からA6へ分割し、各Stageで停止して検証する必要がある
- current specification: 今回はA0のみを完了し、A1以降へ進まない
- technical problem: 先行作業で作成済みのA1相当コードと、今回のA0停止条件を混同しやすい
- options: 作成済み成果物を削除、別リポジトリへ分離、成果物へ含めてA1機能追加を凍結
- recommended option: 既作成成果物は保持し、A0 QAで準備的実装として明示し、A1の新規変更を停止する
- impact: A0成果物の再利用性を維持しつつ、Stage Gateを守る
- decision: 採用

## ADR-0010: A0 availability matrix

- issue: データが存在することと、計算・公開できることを区別する必要がある
- current specification: A0で利用可能性、精度、リスク、次Stageの入力条件を確定する
- technical problem: GTFS、OD、物流、救援施設はcoverageと利用条件が事業者・データセットごとに異なる
- options: 有無だけの一覧、データセット別の可用性・ライセンス・精度・リスク台帳
- recommended option: DATA_AVAILABILITY_MATRIX.mdを作り、○△×と次Stage Gateを記録する
- impact: A1以降で未確認データを公式入力として扱うことを防ぐ
- decision: 採用
