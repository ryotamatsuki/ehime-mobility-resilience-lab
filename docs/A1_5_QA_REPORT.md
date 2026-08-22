# A1.5 QA Report — Official Hospital Data Gate

判定: **PASS WITH WARNINGS / merge可**

基準日: 2026-08-22

## 検証対象

- 公式医療機関Excelの一時取得
- XLSXスキーマ読み取り
- 活動中病院抽出
- OSM hospitalとの名称・距離照合
- 1公式病院=1 OSM featureの重複排除
- A1.5 Accessibility再計算
- Public bundleへの公式原データ漏えい防止
- A1.3/A1.4 Planning Canvasとの接続

## PASS

### 1. 公式ソース取得

愛媛県医療対策課の2026年8月1日時点基本情報ExcelをCIで取得可能。

Raw workbookはrepositoryへ保存していない。

### 2. ログ最小化

初期schema probeはsample rowをActions logへ出していたため修正した。現在のprobeは、件数・必要schemaの成否だけを出力し、施設名・住所・座標等の行情報を出力しない。

### 3. 1対1照合

初回A1.5試行では公式5病院に対してOSM 7 featureが照合され、同一病院のnode/way重複を検出した。

照合アルゴリズムを1対1 assignmentへ修正し、再実行後は:

- official hospitals: 5
- OSM hospital features: 7
- verified public destinations: 5
- excluded duplicate/unverified OSM features: 2
- unmatched official hospitals: 0

となった。

### 4. Public bundle leakage gate

CIで以下を確認した。

- raw workbook未配信
- `facilities.geojson` 全featureが `officially_verified=true`
- official ID未配信
- official name未配信
- official address未配信
- official coordinates未配信

### 5. Accessibility再計算

実データで再計算しPASS。

- GTFS stops: 37/37 snapped
- population zones: 1,840
- hospital destinations: 5
- +1分超悪化人口: 2,030.3675人相当
- mean travel-time change: +0.732分

### 6. Regression

- Python tests PASS
- A0 foundation checks PASS
- A1 source probe PASS
- official workbook schema probe PASS
- planning-canvas source smoke PASS
- generated-site smoke PASS
- mobile contract PASS

## Warning

### W1. 公式Excelの再利用条件

県公式Webページの掲載データであり、オープンデータカタログのCC BYデータとしては扱っていない。A1.5では照合のみに用い、raw/公式属性を公開しない保守的運用とする。

### W2. OSM位置精度

公開病院点の位置・名称はOSM由来である。公式台帳と照合できたことは位置測量精度を保証しない。

### W3. Walking transfer未実装

近接GTFS停留所間の徒歩乗換はまだ時刻表ルーティングへ組み込まれていない。これは次Stepの主要モデル課題。

### W4. 対象範囲

大洲市ぐるりんおおず停留所bbox周辺の縦切りであり、愛媛県全域を意味しない。

## Blocker

なし。

## 次Step

**A1.6 Stop-to-Stop Walking Transfer** を推奨する。

徒歩ネットワーク上で近接するGTFS停留所間のtransfer edgeを生成し、Connection Scanの時刻依存ルーティングに導入する。実装後はA1.5と同一入力でBefore/Afterを再計算し、モデル改善による指標差を回帰比較する。
