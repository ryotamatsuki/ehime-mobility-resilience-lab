# A1.5 — Official Hospital Data Gate

更新日: 2026-08-22

## 目的

A1.1では病院目的地をOpenStreetMap `amenity=hospital` のみから取得していた。A1.5では、愛媛県医療対策課が公開する「医療機関の報告内容（基本情報）」2026年8月1日時点Excelを、現行病院であることを確認する公式Gateとして追加した。

本Stageの目的は、公式Excelそのものを公開GIS化することではなく、公開WebGISで分析対象にするOSM病院が現行の公式医療機関台帳と整合することを確認することである。

## 利用データ

- 愛媛県 医療機関の報告内容（基本情報）
  - 公開元: 愛媛県医療対策課
  - 基準日: 2026-08-01
  - Landing page: https://www.pref.ehime.jp/page/50405.html
  - 取得形式: XLSX
- OpenStreetMap
  - 公開位置・公開名称・徒歩ネットワーク
  - ODbL 1.0

## ライセンス保守方針

県公式Excelは通常の県公式Webページで公開されており、本プロジェクトではオープンデータカタログ上のCC BYデータであるとは扱わない。

そのため以下をRelease Gateとする。

1. Excel原本をGitHubへcommitしない。
2. Excel原本をGitHub Actions artifactへ含めない。
3. 公式台帳の行、住所、公式座標、機関コードをPagesへ配信しない。
4. GitHub Actions logへ施設行を出力しない。
5. 公式台帳は実行時に一時取得し、現行性確認の照合にのみ利用する。
6. Pagesへ配信する施設の位置・名称はOSM由来とする。
7. 公式台帳との照合結果だけを `officially_verified=true` として公開成果物に保持する。

## 照合ロジック

公式台帳から以下を満たす病院だけを内部候補とする。

- `機関区分 == 1`
- `活動区分 == 活動中`
- 緯度経度が有効
- A1分析bbox内

OSM病院との照合は次の順序で行う。

1. 正規化名称が互換かつ350m以内のnamed OSM病院を優先。
2. 名称のないOSM hospitalは120m以内の場合のみ候補。
3. 1つの公式病院に複数OSM featureが対応する場合は1件だけ採用。
4. 1つのOSM featureを複数公式病院へ対応させない。
5. 未照合OSM病院はAccessibility目的地から除外。

名称正規化ではUnicode NFKC、空白・記号除去、`医療法人`等の法人種別文字列除去を行う。

## 実データ結果

2026-08-22 GitHub Actions実行結果:

| 指標 | 件数 |
|---|---:|
| 公式台帳の活動中病院（A1 bbox内） | 5 |
| OSM hospital表現 | 7 |
| 公式台帳と1対1照合できたOSM病院 | 5 |
| 重複・未照合として除外したOSM hospital | 2 |
| 公式台帳側の未照合病院 | 0 |

したがって、A1.5の病院目的地は5件とする。

## Accessibilityへの影響

病院目的地の重複を除去して再計算した結果:

- 1分超所要時間悪化人口: 2,030.3675人相当
- 人口加重平均所要時間の悪化: +0.732分
- 30分圏人口損失: 0人相当
- 60分圏人口損失: 0人相当

A1.1の7 OSM表現をそのまま用いた場合は、1分超悪化人口1,955.289人相当、平均悪化+0.722分だった。施設定義の品質管理によりモデル出力も変化するため、目的地データのprovenanceをRelease Gateに含める必要がある。

## 公開成果物

`facilities.geojson` には次のOSM由来情報だけを保持する。

- OSM位置
- OSM名称
- amenity
- walking networkへのsnap距離
- `officially_verified`
- verification distance

次を含めない。

- 公式機関コード
- 公式名称
- 公式住所
- 公式緯度経度
- Excel行データ

## 残課題

A1.5では病院現行性Gateを解消した。次のA1小Stepはstop-to-stop walking transferであり、徒歩で近接する別停留所への乗換を時刻依存公共交通ネットワークへ導入する。
