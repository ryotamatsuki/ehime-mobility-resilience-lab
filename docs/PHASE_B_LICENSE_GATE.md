# Phase B License Gate

## 状態

現状：BLOCKED

Phase Aは、愛媛県新地震被害想定GISなしで成立する。Phase Bの原データ、加工物、派生レイヤー、スクリーンショット、ハザード値付与道路は、このゲートがPASSになるまで取得・加工・公開しない。

## 必須の書面確認

1. 座標変換の可否
2. clipping、intersection、spatial joinの可否
3. raster/vector変換の可否
4. 派生数値・再分類・ハザード値付与の可否
5. Web表示、スクリーンショット、デモ動画の可否
6. GitHubとGitHub Pagesでの公開可否
7. 原GISを含まない派生GeoJSON、タイル、表の再配布可否
8. CC BY-NC-NDとコンペ応募、非営利PoC、公開リポジトリの関係
9. 更新版・第三者データの扱い
10. attributionと免責文の指定

## 許諾取得後のAdapter interface

許諾がPASSした場合に限り、Hazard Adapterは次の入力と出力だけを契約化する。

- 入力：許諾済みのhazard dataset version、CRS、対象範囲、属性名
- 処理：許諾された変換だけを明示した処理レシピ
- 出力：ユーザー仮定Dとしての閉鎖、容量低下、速度低下の候補条件
- 監査：許諾文書ID、原データchecksum、変換ログ、生成git_sha
- 境界：Hazard Adapterは交通Stress Test条件を生成するだけで、実被害予測を主張しない

## CI / Release rule

許諾文書がない状態では、Phase Bディレクトリ、データ、派生GeoJSON、ハザード入力を公開bundleに含めない。Phase AのCIはHazard Adapterが存在しない状態でも全テストと公開ビルドが成功することを要求する。
