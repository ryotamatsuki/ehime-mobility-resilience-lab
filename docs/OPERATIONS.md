# Operations and Data Update Center

## 運用原則

直接上書きは禁止する。更新は候補版として隔離し、自動Validation、旧版との差分、プレビュー、承認、active切替を経て公開する。active版はいつでもarchived版へrollbackできる。

## 対応形式

GTFS ZIP、CSV、XLSX、GeoJSON、Shapefile ZIP、GeoPackageを受け付ける。サーバー側の管理画面はGitHub Pagesへ置かず、管理者環境で起動する。

## 更新フロー

1. dataset_id、データ名、source、license、reference_dateを入力する。
2. ファイルをcandidate領域へ保存し、checksumとimported_atを計算する。
3. 拡張子、MIME、サイズ、ZIP展開安全性、必須列、CRS、geometry、ID整合性を検証する。
4. 旧active版との件数、追加、削除、属性変更、座標変更を表示する。
5. プレビューと検証結果を人が確認する。
6. 承認後にactiveへ切り替え、旧版をarchivedとして保持する。
7. manifestとprovenanceを再生成し、公開bundleを再ビルドする。

## Version record

各版はdataset_id、dataset_name、source、license、reference_date、imported_at、checksum、schema_version、validation_status、statusを持つ。statusはcandidate、validated、active、archivedのいずれかである。

## Rollback

rollbackは旧版を削除せず、指定版をactiveへ再指定する。Scenarioの過去結果はresult_versionと入力版を保持し、最新データで再計算した結果と混同しない。

## 非エンジニア向け表示

画面では、検証済み、承認待ち、現在使用中、過去版、利用条件未確認を日本語で表示する。専門用語だけで更新を要求せず、エラーには修正対象と再アップロード方法を表示する。

## 重要な制約

ODPT認証情報、個人情報、非公開在庫、Phase BハザードGISをアップロードしない。ライセンス不明の候補版は公開へ切り替えられない。
