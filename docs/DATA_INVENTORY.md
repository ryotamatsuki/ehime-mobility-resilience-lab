# Data Inventory

調査基準日：2026年8月22日（JST）

この表は、取得できたデータ、外部入力、未取得データを混同しないための台帳である。URLやライセンスは個別の利用条件を優先し、未確認データは実装入力として扱わない。

| dataset | source | url | license | reference_date | spatial_resolution | format | CRS | update_frequency | usage | confidence | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OSM Ehime major roads | OpenStreetMap / Overpass | https://www.openstreetmap.org/copyright | ODbL 1.0 | 取得スナップショット | 道路way | Overpass JSON / GeoJSON | WGS84 | 取得時点 | 道路グラフ、経路・閉鎖Stress Test | B | 県内 trunk・primary・secondary の縮約。抽出日時・クエリ・attributionを保存 |
| R3 road census Ehime | 国土交通省 道路交通センサス | https://www.mlit.go.jp/road/census/r3/index.html | 国土交通省利用規約・個別条件 | 2021年度 | 調査区間・地点 | CSV | 表データ | 調査周期 | 観測交通量、校正・holdout | A | kasyo38.csv と zkntrf38.csv を取得。道路リンク対応はB加工値 |
| R6 future population mesh 500m | 国土交通省 国土数値情報 | https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-mesh500r6.html | CC BY 4.0 | 2020 Census基準、2025等推計 | 500m mesh | GeoJSON / ZIP | JGD2011 | 公開更新時 | 人口、年齢、到達可能人口の分母 | B | Ehime zipを取得。公開用は集約成果物に縮約 |
| R2 census municipality commuting OD | e-Stat / 総務省統計局 | https://www.e-stat.go.jp/stat-search/database | e-Stat利用規約 | 2020 | 市区町村間 | CSV / Excel / API | 表データ | 調査周期 | 通勤・通学の市町間総量制約 | A/B | 県内詳細の車両ODではない。実取得版を未登録のまま公式値としない |
| R3 automobile OD | 国土交通省・e-Stat | https://www.e-stat.go.jp/stat-search?iroha=14 | e-Stat利用規約 | 2021 | 都道府県間等 | Excel / CSV | 表データ | 調査周期 | 県外ゲートウェイと広域総量 | A/B | 県内メッシュODの代替ではない |
| R3 economic census mesh | 総務省統計局・e-Stat | https://www.e-stat.go.jp/gis/statmap-search | e-Stat利用規約 | 2021 | 500m / 1km mesh | CSV / GIS | JGD2011 | 調査周期 | 発生・集中の分布制約 | B | 未取得。実装時に取得日・版を追加 |
| freight census | 国土交通省 全国貨物純流動調査 | https://www.mlit.go.jp/sogoseisaku/transport/sosei_transport_fr_000074.html | 公開統計の個別条件 | 2021 | 県・産業・品目等 | Excel / CSV | 表データ | 調査周期 | 貨物の広域総量 | A/B | 企業在庫や完全な企業間サプライチェーンではない |
| Ehime open data shelters | 愛媛県 | https://www.pref.ehime.jp/opendata-catalog/ | 原則 CC BY 4.0、個別条件優先 | 公開版ごと | 施設 | XLSX / CSV | 座標確認要 | 更新時 | 避難所・救援物流候補 | B | 住所だけの場合の位置付与は加工値として別管理 |
| Ehime port statistics | 愛媛県 | https://www.pref.ehime.jp/opendata-catalog/dataset/dataland-228.html | 個別ページ確認要 | 2022実績等 | 港湾集計 | XLSX | 表データ | 年次 | 港湾需要・物流ノード | A/B | 港湾形状とは別データ |
| medical facilities | 国土数値情報 | https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P04-v3_0.html | 国土数値情報利用規約 | 2020年度等 | 点 | GML / Shapefile / GeoJSON | JGD2011 | 更新時 | 病院・災害拠点病院候補 | B | 現行指定は別途照合する |
| Iyo Railway bus GTFS | ODPT | https://ckan.odpt.org/dataset/iyotetsu_bus_all_lines | 基本ライセンス・個別規約・登録条件 | 取得版のfeed_info | 停留所・便・路線 | GTFS ZIP | WGS84 | 事業者更新 | 公共交通アクセシビリティ | A/B | 認証・規約確認前は生ZIPをcommit・Pages配信しない |
| Iyo Railway bus GTFS-RT | ODPT | https://ckan.odpt.org/dataset/odpt_iyotetsu_bus_all_lines | 基本ライセンス・個別規約・登録条件 | 取得時点 | 車両・便 | Protobuf | WGS84 | リアルタイム | Phase Aの固定入力検証のみ | A | 長期キャッシュや認証情報を公開しない |
| Ozu Gururin GTFS | 大洲市 | https://www.city.ozu.ehime.jp/site/opendata/44871.html | CC BY 4.0の掲載条件を確認 | 取得版 | 停留所・便・路線 | GTFS ZIP | WGS84 | 事業者更新 | 公共交通fixture候補 | A/B | 実取得・期間確認後に公開版へ追加 |
| Project LINKS warehouse | 国土交通省 | https://www.mlit.go.jp/links/ | 個別データセット確認要 | 公開版ごと | 施設等 | CKAN resource | 要確認 | 更新時 | 物流拠点 | 未確定 | ライセンス・項目・再配布条件を確認するまで使用しない |
| Ehime hazard GIS | 愛媛県 | https://www.pref.ehime.jp/opendata-catalog/dataset/3790.html | CC BY-NC-ND掲載、許諾要 | 2026更新版 | GIS | ZIP | 要確認 | 更新時 | Phase B adapterのみ | blocked | 許諾取得前は取得後の加工・派生・公開を行わない |

## 現在の取得実績

- R3道路交通センサスのEhime CSVを取得し、形式と件数を確認した。
- OSM Overpassから県内主要道路のスナップショットを取得した。
- R6 500m将来人口メッシュのEhime GeoJSON ZIPを取得し、7,857 featureを確認した。
- GTFS Data Japan APIは基準日時点で愛媛・伊予鉄・松山の検索結果が0件だった。これは全提供元の不存在を意味しないため、未取得の外部入力として扱う。

## 未取得データの扱い

未取得の国勢調査OD、経済センサス、物流センサス、避難所座標、災害拠点病院の現行一覧を、存在するデータとして補完しない。公開版の入力状態はmanifestで unavailable または external_input と表示する。
