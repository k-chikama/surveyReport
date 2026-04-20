# CLAUDE.md — Claude Code 向けプロジェクトガイド

## プロジェクト概要

アンケート集計データを入力して PDF レポートを自動生成する Streamlit Web アプリ。
手動入力 UI と、macOS の Apple Vision OCR + ollama LLM による自動読み取りを組み合わせたシステム。

## アーキテクチャ

```
app.py                  ← Streamlit エントリーポイント（UI・セッション管理）
  └─ pdf_generator.py   ← PDF生成（グラフ描画・ReportLab組版）
  └─ ocr_reader.py      ← OCR読み取り・LLM解析（macOS専用）

data.py                 ← サンプルデータ（SECTIONS, BASE 定数）
report_bar.py           ← CLI用 縦棒グラフPDF生成スクリプト（data.py 参照）
report_pie.py           ← CLI用 円グラフPDF生成スクリプト（data.py 参照）

fonts/NotoSansJP-Regular.ttf  ← 日本語フォント（必須）
output/                       ← PDF 出力先（.gitignore 対象）
```

## 主要モジュールの役割

### app.py
- Streamlit のセッション状態 (`st.session_state.sections`) で設問リストを管理
- 設問データの形式: `[{"title": str, "note": str, "items": [{"label": str, "count": int}]}, ...]`
- `sections_to_pdf_format()` で PDF 生成用フォーマット `[(label, count), ...]` に変換
- タブ構成: データ入力 / プレビュー / PDF出力

### pdf_generator.py
- `generate_pdf(sections, base, report_title, graph_type)` が公開インターフェース
- 戻り値は PDF の `bytes`（Streamlit の `download_button` に直接渡せる）
- グラフ種類: `"縦棒グラフ"` / `"円グラフ"` / `"横棒グラフ"`
- フォントは `fonts/NotoSansJP-Regular.ttf` をハードパスで参照（フォールバックなし）

### ocr_reader.py
- `image_to_all_questions(pil_image, llm_model)` → `([QuestionStructure], raw_lines, used_llm)`
- 処理フロー: Apple Vision OCR → ollama LLM 解析 → 正規表現フォールバック
- `is_ocr_available()` / `is_ollama_available()` で機能可用性チェック可能
- macOS 以外では Vision / Quartz がインポートできず OCR 不可

## 開発ルール

### フォント
- `fonts/NotoSansJP-Regular.ttf` は必須ファイル。削除・移動禁止
- matplotlib と ReportLab の両方に同じフォントを設定している（`pdf_generator.py:40-43`）

### セッション状態のキー
- `st.session_state.sections`: 設問リスト本体
- `st.session_state.row_count`: 入力行数
- `st.session_state[f"pdf_{gtype}"]`: 生成済み PDF bytes のキャッシュ

### データフォーマット変換
```
UI (session_state.sections)        pdf_generator 用
[{                            →    [{
  "title": str,                      "title": str,
  "note": str,                       "note": str,
  "items": [                         "items": [
    {"label": str, "count": int}       (str, int),   ← タプル
  ]                                  ]
}]                                 }]
```

## よく使うコマンド

```bash
# アプリ起動
streamlit run app.py

# 縦棒グラフPDFを直接生成（data.py のサンプルデータ使用）
python report_bar.py

# 円グラフPDFを直接生成
python report_pie.py

# 依存パッケージ確認
pip list | grep -E "streamlit|matplotlib|reportlab|pandas|pillow|ollama|pyobjc"
```

## 依存パッケージ

| パッケージ | 用途 | 必須 |
|---|---|---|
| streamlit | Web UI | 必須 |
| matplotlib | グラフ描画 | 必須 |
| reportlab | PDF組版 | 必須 |
| pandas | プレビューのDataFrame表示 | 必須 |
| pillow | 画像処理（OCR用） | OCR使用時 |
| pyobjc-framework-Vision | Apple Vision OCR | macOSのみ |
| pyobjc-framework-Quartz | 画像ファイルハンドリング | macOSのみ |
| ollama | LLM解析 | 任意（高精度OCR） |

## 注意事項

- `output/` ディレクトリは `.gitignore` で除外されている。生成PDFはコミットしない
- `.idea/` も除外済み（PyCharm プロジェクト設定）
- `data.py` には実際のアンケート集計データが含まれる（サンプルとして物価高に関するアンケート290人分）
- `report_bar.py` / `report_pie.py` は Streamlit 版に統合される前のレガシースクリプト。新機能は `pdf_generator.py` に追加する

## 今後の開発候補

- [ ] `requirements.txt` の作成
- [ ] OCR 機能の Streamlit UI への組み込み（`ocr_reader.py` は実装済みだが UI 未接続）
- [ ] 複数アンケートのバッチ処理
- [ ] グラフの色・スタイルカスタマイズ UI
- [ ] PDF テンプレートの選択機能
