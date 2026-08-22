# Ehime Mobility Resilience Lab

「もし、ここが通れなくなったら。」

公共交通・道路・物流を構成する交通ネットワークを平時に意図的にストレステストし、愛媛県内の人・車・物の移動への影響を説明可能な形で検証する、GitHub Pages公開型のWebGISとPython分析基盤です。

## Single Source of Truth

開発の正式仕様は、次の文書です。

- [開発仕様書 Version 1.0](docs/SPECIFICATION.md)
- [A0アーキテクチャ設計](docs/ARCHITECTURE.md)

Phase Aは愛媛県新地震被害想定GISに依存しません。公式値・加工値・モデル推計値・ユーザー仮定を区別し、結果には使用データ・モデル・パラメータ・生成日時を付与します。

## Status

現在はStage A0（Foundation / Data Feasibility）です。分析エンジンや完成版WebGISは、A0のRelease Gate確認後に段階的に実装します。
