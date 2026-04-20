# アンケート集計レポート生成システム

アンケートの集計データを入力し、PDF レポートを自動生成する Streamlit Web アプリです。

## 機能

- **手動入力モード**: Web UI からアンケートの設問・回答・人数を入力して PDF を生成
- **OCR 読み込みモード**: アンケート用紙の画像から設問構造を自動抽出（macOS 専用）
  - Apple Vision フレームワークによる日本語 OCR
  - ollama（ローカル LLM）による高精度な設問構造解析
- **PDF 出力**: 縦棒グラフ / 円グラフ / 横棒グラフの 3 種類に対応
- **データ管理**: JSON でのエクスポート・インポートに対応

## スクリーンショット

| データ入力 | プレビュー | PDF出力 |
|---|---|---|
| 設問・回答・人数を入力 | グラフプレビュー表示 | 3種類のグラフでPDF生成 |

## セットアップ

### 必要環境

- Python 3.10 以上
- macOS（OCR 機能を使用する場合）

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/k-chikama/surveyReport.git
cd surveyReport

# 仮想環境を作成（推奨）
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# .venv\Scripts\activate   # Windows

# 依存パッケージをインストール
pip install -r requirements.txt
```

### 依存パッケージ

`requirements.txt` がない場合は以下を手動でインストールしてください。

```bash
pip install streamlit matplotlib reportlab pandas pillow

# OCR 機能を使用する場合（macOS のみ）
pip install pyobjc-framework-Vision pyobjc-framework-Quartz

# LLM 解析を使用する場合
pip install ollama
```

## 使い方

### アプリ起動

```bash
streamlit run app.py
```

ブラウザで `http://localhost:8501` が自動的に開きます。

### 基本的な操作フロー

1. **サイドバー**でレポートタイトル・集計ベース・グラフ種類を設定
2. **「データ入力」タブ**で設問を追加
   - 設問タイトル・補足メモを入力
   - 回答項目と人数を入力
   - 「✅ この設問を追加」をクリック
3. **「プレビュー」タブ**でグラフを確認
4. **「PDF出力」タブ**でPDFを生成・ダウンロード

### データの保存と読み込み

- サイドバーの「📥 データをJSONで保存」で入力データを保存
- 「📤 JSONデータを読み込む」で保存したデータを復元

### OCR機能（macOS のみ）

アンケート用紙の画像を読み込んで設問構造を自動抽出します。

```bash
# ollama をインストール（推奨）
# https://ollama.com からインストーラーをダウンロード

# 日本語対応モデルを取得（どれか1つ）
ollama pull qwen2.5:3b   # 軽量・高速
ollama pull gemma3:4b    # バランス型
ollama pull llama3.2:3b  # Meta製
```

## ファイル構成

```
surveyReport/
├── app.py              # Streamlit メインアプリ
├── pdf_generator.py    # PDF生成モジュール（3種グラフ対応）
├── ocr_reader.py       # OCR + LLM解析モジュール（macOS専用）
├── data.py             # サンプルデータ定義
├── report_bar.py       # 縦棒グラフ PDF 単体生成スクリプト
├── report_pie.py       # 円グラフ PDF 単体生成スクリプト
├── fonts/
│   └── NotoSansJP-Regular.ttf  # 日本語フォント
└── output/             # 生成したPDFの出力先（.gitignore対象）
```

## 単体スクリプトでの PDF 生成

`data.py` のデータを使って直接 PDF を生成することもできます。

```bash
python report_bar.py   # 縦棒グラフ版 → output/report_bar.pdf
python report_pie.py   # 円グラフ版   → output/report_pie.pdf
```

## 技術スタック

| 用途 | ライブラリ |
|---|---|
| Web UI | [Streamlit](https://streamlit.io/) |
| グラフ描画 | [matplotlib](https://matplotlib.org/) |
| PDF生成 | [ReportLab](https://www.reportlab.com/) |
| OCR | Apple Vision Framework (pyobjc) |
| LLM解析 | [ollama](https://ollama.com/) |
| 日本語フォント | Noto Sans JP |

## トラブルシューティング

### フォントエラー

```
[ERROR] フォントファイルが見つかりません: fonts/NotoSansJP-Regular.ttf
```

`fonts/` ディレクトリに `NotoSansJP-Regular.ttf` が存在するか確認してください。
[Google Fonts](https://fonts.google.com/noto/specimen/Noto+Sans+JP) からダウンロード可能です。

### OCR が動かない

- macOS 以外の環境では OCR 機能は動作しません
- `pip install pyobjc-framework-Vision pyobjc-framework-Quartz` を実行してください

### ollama が使えない

- [https://ollama.com](https://ollama.com) からアプリをインストールして起動してください
- `ollama list` でモデルが存在するか確認してください
- ollama が使えない場合は正規表現ベースのフォールバックパーサーが動作します
