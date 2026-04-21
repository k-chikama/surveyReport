# -*- coding: utf-8 -*-
import streamlit as st
import json
import os

from pdf_generator import generate_pdf
from ocr_gcv import is_gcv_available, image_to_questions

try:
    from streamlit_local_storage import LocalStorage
    _ls = LocalStorage()
    _LS_OK = True
except Exception:
    _ls = None
    _LS_OK = False

# ─────────────────────────────────────────────
# ページ設定
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="アンケートレポート生成",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
/* ── 全体 ── */
[data-testid="stAppViewContainer"] {
    background: #f4f6fb;
}
[data-testid="stHeader"] {
    background: transparent;
}

/* ── サイドバー ── */
[data-testid="stSidebar"] {
    background: #1a3c5e;
}
[data-testid="stSidebar"] * {
    color: #e8f0fa !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stTextInput label {
    color: #b0c8e8 !important;
    font-size: 0.85rem !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #ffffff !important;
}
[data-testid="stSidebar"] hr {
    border-color: #2e5a8a !important;
}
[data-testid="stSidebar"] .stDownloadButton button {
    background: #2e5a8a !important;
    border: 1px solid #4a80b8 !important;
    color: #fff !important;
    width: 100%;
}

/* ── タブ ── */
[data-testid="stTabs"] [role="tablist"] {
    background: #fff;
    border-radius: 12px 12px 0 0;
    padding: 4px 8px 0;
    gap: 4px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
[data-testid="stTabs"] button[role="tab"] {
    border-radius: 8px 8px 0 0 !important;
    font-weight: 500;
    padding: 8px 18px !important;
    color: #5a7a9a !important;
    transition: all 0.2s;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    background: #1a3c5e !important;
    color: #fff !important;
}
[data-testid="stTabs"] [role="tabpanel"] {
    background: #fff;
    border-radius: 0 12px 12px 12px;
    padding: 24px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    min-height: 400px;
}

/* ── ボタン ── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1a3c5e, #3a7ebf) !important;
    border: none !important;
    color: #fff !important;
    box-shadow: 0 2px 6px rgba(58,126,191,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 4px 12px rgba(58,126,191,0.5) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: #fff !important;
    border: 1px solid #d0dce8 !important;
    color: #1a3c5e !important;
}

/* ── 入力欄（メインエリア） ── */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    border-radius: 8px !important;
    border: 1px solid #d0dce8 !important;
    background: #fafdff !important;
    color: #1a2a3a !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #3a7ebf !important;
    box-shadow: 0 0 0 2px rgba(58,126,191,0.15) !important;
}

/* ── サイドバー内の入力欄 ── */
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stTextArea textarea,
[data-testid="stSidebar"] .stNumberInput input {
    background: #2e5a8a !important;
    border: 1px solid #4a80b8 !important;
    border-radius: 8px !important;
    color: #ffffff !important;
}
[data-testid="stSidebar"] .stTextInput input::placeholder,
[data-testid="stSidebar"] .stTextArea textarea::placeholder {
    color: #8aaac8 !important;
}

/* ── サイドバー セレクトボックス ── */
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {
    background: #2e5a8a !important;
    border: 1px solid #4a80b8 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span,
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] div {
    color: #ffffff !important;
}
[data-testid="stSidebar"] .stSelectbox svg {
    fill: #b0c8e8 !important;
}

/* ── サイドバー ファイルアップローダー ── */
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background: #2e5a8a !important;
    border: 1px dashed #4a80b8 !important;
    border-radius: 10px !important;
    padding: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] span,
[data-testid="stSidebar"] [data-testid="stFileUploader"] p,
[data-testid="stSidebar"] [data-testid="stFileUploader"] small {
    color: #b0c8e8 !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    background: #2e5a8a !important;
    border: 1px dashed #4a80b8 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
    background: #1a3c5e !important;
    color: #fff !important;
    border: 1px solid #4a80b8 !important;
    border-radius: 6px !important;
}

/* ── expander ── */
[data-testid="stExpander"] {
    border: 1px solid #e2eaf3 !important;
    border-radius: 10px !important;
    background: #fafdff !important;
    margin-bottom: 8px !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    color: #1a3c5e !important;
}

/* ── info / success / warning ── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
}

/* ── divider ── */
hr {
    border-color: #e2eaf3 !important;
}

/* ── dataframe ── */
[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow: hidden !important;
}
</style>
""", unsafe_allow_html=True)

# ── ヘッダー
st.markdown("""
<div style="
    background: linear-gradient(135deg, #1a3c5e 0%, #3a7ebf 100%);
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 20px;
    box-shadow: 0 4px 16px rgba(26,60,94,0.25);
">
    <h1 style="color:#fff; margin:0; font-size:1.8rem; font-weight:700;">
        📊 アンケート集計レポート生成システム
    </h1>
    <p style="color:#b8d4f0; margin:8px 0 0; font-size:0.95rem;">
        アンケートデータを入力してグラフ付きPDFレポートを自動生成します
    </p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# セッション状態の初期化（localStorage からの復元含む）
# ─────────────────────────────────────────────
if "sections" not in st.session_state:
    st.session_state.sections = []

if "past_sections" not in st.session_state:
    st.session_state.past_sections = []  # [{"title":str,"note":str,"items":[{"label":str}]}, ...]

if "storage_loaded" not in st.session_state:
    if _LS_OK:
        _saved = _ls.getItem("survey_data")
        if _saved is not None:
            # コンポーネントからデータが届いた
            try:
                _data = json.loads(_saved)
                st.session_state.sections = _data.get("sections", [])
                st.session_state.past_sections = _data.get("past_sections", [])
            except Exception:
                pass
            st.session_state.storage_loaded = True
        else:
            # None の場合：コンポーネント未初期化 or データなし
            # 2回試行してもNoneならデータなしと確定する
            _attempts = st.session_state.get("_ls_attempts", 0) + 1
            st.session_state["_ls_attempts"] = _attempts
            if _attempts >= 2:
                st.session_state.storage_loaded = True
    else:
        st.session_state.storage_loaded = True

if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

if "tab_pending_fill" in st.session_state:
    _t = st.session_state.pop("tab_pending_fill")
    st.session_state["tab_q_title"] = _t["title"]
    st.session_state["tab_q_note"] = _t["note"]
    st.session_state.row_count = max(4, len(_t["items"]))
    for _i, _item in enumerate(_t["items"]):
        st.session_state[f"label_{_i}"] = _item["label"]

# ─────────────────────────────────────────────
# ヘルパー
# ─────────────────────────────────────────────
def sections_to_pdf_format(sections_state):
    result = []
    for sec in sections_state:
        items = [(row["label"], int(row["count"])) for row in sec["items"] if row["label"].strip()]
        result.append({"title": sec["title"], "note": sec.get("note", ""), "items": items})
    return result

def calc_base(sections_state):
    for sec in sections_state:
        total = sum(int(r["count"]) for r in sec["items"] if r["label"].strip())
        if total > 0:
            return total
    return 1

def _merge_past_sections(new_sec):
    """past_sections に新しい設問を追加（タイトル重複は上書き）"""
    entry = {"title": new_sec["title"], "note": new_sec.get("note", ""),
             "items": [{"label": r["label"]} for r in new_sec["items"] if r["label"].strip()]}
    existing = [s for s in st.session_state.past_sections if s["title"] != entry["title"]]
    st.session_state.past_sections = existing + [entry]

def save_to_storage(new_sec=None):
    if new_sec:
        _merge_past_sections(new_sec)
    if not _LS_OK:
        return
    _ls.setItem("survey_data", json.dumps(
        {"sections": st.session_state.sections, "past_sections": st.session_state.past_sections},
        ensure_ascii=False,
    ), key="ls_set_survey_data")

def clear_storage():
    if not _LS_OK:
        return
    st.session_state.past_sections = []
    _ls.setItem("survey_data", json.dumps(
        {"sections": [], "past_sections": []},
        ensure_ascii=False,
    ), key="ls_set_survey_data")

# ─────────────────────────────────────────────
# サイドバー：レポート設定
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ レポート設定")

    report_title = st.text_input("レポートタイトル", value="アンケート調査結果報告書")

    base_mode = st.radio("集計ベース（分母）", ["自動（最初の設問の合計）", "手動で指定"], index=0)
    if base_mode == "手動で指定":
        base_value = st.number_input("集計ベース人数", min_value=1, value=290, step=1)
    else:
        base_value = None

    graph_type = st.selectbox("グラフ種類", ["縦棒グラフ", "円グラフ", "横棒グラフ"], index=0)

    st.divider()
    st.markdown("### 💾 データ管理")

    if st.session_state.sections:
        json_str = json.dumps(st.session_state.sections, ensure_ascii=False, indent=2)
        st.download_button(
            "📥 データをJSONで保存",
            data=json_str.encode("utf-8"),
            file_name="survey_data.json",
            mime="application/json",
        )

    uploaded_json = st.file_uploader("📤 JSONデータを読み込む", type=["json"], key="json_uploader")
    if uploaded_json is not None:
        try:
            raw = uploaded_json.read()
            loaded = json.loads(raw.decode("utf-8"))
            if not isinstance(loaded, list):
                st.error(f"JSONの形式が正しくありません（リスト形式が必要です）")
            else:
                st.session_state.sections = loaded
                st.session_state.past_sections = st.session_state.get("past_sections", [])
                st.session_state.storage_loaded = True
                save_to_storage(None)
                st.toast(f"{len(loaded)}件の設問を読み込みました ✅")
                st.rerun()
        except Exception as e:
            st.error(f"読み込みエラー: {e}")

# ─────────────────────────────────────────────
# メインエリア：タブ構成
# ─────────────────────────────────────────────
tab_help, tab_ocr, tab_input, tab_preview, tab_export = st.tabs(["❓ 使い方", "📷 OCR読み取り", "📝 データ入力", "👁️ プレビュー", "📄 PDF出力"])

# ══════════════════════════════════════════════
# タブ0：使い方
# ══════════════════════════════════════════════
with tab_help:
    st.subheader("❓ このアプリの使い方")
    st.markdown("アンケートの集計データを入力して、グラフ付きのPDFレポートを自動で作成するアプリです。")
    st.divider()

    with st.expander("📋 基本的な流れ（まずここを読んでください）", expanded=True):
        st.markdown("""
**アンケート結果をPDFにするまでの3ステップ**

1. **データ入力タブ** でアンケートの設問と回答人数を入力する
2. **プレビュータブ** でグラフを確認する
3. **PDF出力タブ** でPDFを生成してダウンロードする

---
💡 **画像（写真）から自動で読み取りたい場合**は「📷 OCR読み取り」タブを使います（別途設定が必要です）。
""")

    with st.expander("📝 ステップ1：設問とデータを入力する（データ入力タブ）", expanded=False):
        st.markdown("""
### 設問を1つずつ追加する方法

**左側の「設問を追加」エリアで入力します。**

| 入力項目 | 説明 | 例 |
|---|---|---|
| 設問タイトル | アンケートの質問文 | 問1. あなたの性別を教えてください |
| 補足メモ | 注意書き（省略可） | ※ひとつだけ選んでください |
| 回答項目 | 選択肢の名前 | 男性、女性、回答しない |

**入力の手順：**
1. 「設問タイトル」に質問文を入力する
2. 「回答項目」の欄に選択肢を1行ずつ入力する（人数は右の数字欄に入力）
3. 「✅ この設問を追加」ボタンを押す
4. 右側の「登録済み設問一覧」に追加されたことを確認する
5. 繰り返して全設問を入力する

---
### 人数を後から入力・修正する方法

1. 右側の「登録済み設問一覧」から修正したい設問をクリックして開く
2. 各項目の右側に数字入力欄があるので人数を入力する
3. コメント欄（任意）に考察や補足を書ける
4. 「💾 保存」ボタンを押す

---
### まとめて複数の設問を追加したい場合

「💡 過去の設問から追加」を開くと、以前入力した設問を選んで一括追加できます。
""")

    with st.expander("👁️ ステップ2：グラフをプレビューで確認する（プレビュータブ）", expanded=False):
        st.markdown("""
### プレビューの見方

- 入力した設問が順番に表示されます
- 各設問の下に**集計表**と**グラフ**が表示されます
- コメントを入力した設問は、グラフの下にコメントが表示されます

---
### グラフの種類を変えたい場合

**画面左側のサイドバー**（スマホでは画面左上の「>」をタップ）で変更できます。

| グラフ種類 | 向いているケース |
|---|---|
| 縦棒グラフ | 項目を比較したいとき（おすすめ） |
| 円グラフ | 全体の割合を見たいとき |
| 横棒グラフ | 項目名が長いとき |

---
### 集計ベース（分母）について

割合（%）を計算するときの基準人数です。
- **自動**：最初の設問の合計人数が自動で使われます
- **手動**：アンケート配布数など、任意の人数を指定できます
""")

    with st.expander("📄 ステップ3：PDFを生成してダウンロードする（PDF出力タブ）", expanded=False):
        st.markdown("""
### PDFの生成手順

1. **「PDF出力」タブ**をクリックする
2. 縦棒・円・横棒の3種類から使いたいグラフのボタンを押す
3. 「生成完了！」と表示されたら「⬇️ ダウンロード」ボタンを押す
4. PDFファイルがパソコンやスマホに保存される

💡 **3種類まとめて作りたい場合**は「3種類すべてを一括生成」ボタンが便利です。

---
### レポートタイトルを変えたい場合

左側サイドバーの「レポートタイトル」欄を書き換えてください。
""")

    with st.expander("💾 データの保存・読み込みについて", expanded=False):
        st.markdown("""
### 自動保存について

入力したデータは**ブラウザに自動保存**されます。
ページを更新したり、ブラウザを閉じて開き直しても、データは消えません。

---
### JSONファイルで保存・共有する方法

大切なデータのバックアップや、他の端末への引き継ぎに使えます。

**保存する方法：**
1. 左側サイドバーの「📥 データをJSONで保存」ボタンを押す
2. `survey_data.json` というファイルがダウンロードされる

**読み込む方法：**
1. 左側サイドバーの「📤 JSONデータを読み込む」から保存したファイルを選ぶ
2. 自動的にデータが復元される

---
### データを全部消したい場合

「データ入力」タブ → 右側一覧の下の「🗑️ 全設問を削除」ボタンを押してください。
""")

    with st.expander("📷 画像から自動読み取り（OCR読み取りタブ）", expanded=False):
        st.markdown("""
### OCR読み取りとは

アンケート用紙の写真を撮影してアップロードすると、文字を自動で読み取り、
設問のタイトルや選択肢の入力を補助する機能です。

> ⚠️ **この機能を使うには管理者による設定が必要です。** 設定が済んでいない場合は「データ入力」タブから手動で入力してください。

---
### 使い方の流れ

1. 「📷 OCR読み取り」タブを開く
2. アンケート用紙の写真（PNG・JPG）をアップロードする
3. 「🔍 OCRで読み取る」ボタンを押す
4. 左側に読み取ったテキストが表示される
5. 右側の入力欄に、読み取ったテキストをコピー＆ペーストして設問を入力する
6. 「✅ すべて追加」で登録する

---
### コピー＆ペーストのやり方

- **パソコン**：コピーしたいテキストをマウスでドラッグして選択 → `Ctrl+C` でコピー → 入力欄をクリックして `Ctrl+V` で貼り付け
- **スマホ**：コピーしたいテキストを長押しして選択 → 「コピー」 → 入力欄をタップして「ペースト」
""")

    with st.expander("❓ よくある質問", expanded=False):
        st.markdown("""
**Q. データがなくなってしまいました**
→ ブラウザのキャッシュをクリアするとデータが消える場合があります。大切なデータは「📥 JSONで保存」ボタンでバックアップを取ってください。

**Q. グラフの文字が重なって読めません**
→ 項目名が長い場合は「横棒グラフ」に切り替えると見やすくなります。

**Q. スマホから使えますか？**
→ 使えます。スマホのブラウザでアクセスしてください。サイドバーは画面左上の「>」をタップすると開きます。

**Q. 複数回答の設問はどう入力しますか？**
→ 補足メモ欄に「※複数回答可」と入力し、各項目の人数をそのまま入力してください。集計ベースは「手動で指定」でアンケート配布数を入力すると正確な割合が出ます。

**Q. PDFが文字化けしています**
→ アプリ側の問題ではなく、PDFビューアの設定の可能性があります。別のPDFアプリで開いてみてください。
""")

# ══════════════════════════════════════════════
# タブ1：OCR読み取り
# ══════════════════════════════════════════════
with tab_ocr:
    st.subheader("📷 画像からアンケートを読み取る")

    api_key = os.environ.get("GOOGLE_VISION_API_KEY", "")
    if not api_key:
        st.warning("Google Cloud Vision API キーが設定されていません。\nStreamlit Cloud の Settings > Secrets に `GOOGLE_VISION_API_KEY` を追加してください。")
    else:
        uploaded_img = st.file_uploader("アンケート画像をアップロード", type=["png", "jpg", "jpeg"])
        if uploaded_img:
            from PIL import Image as PILImage
            pil_img = PILImage.open(uploaded_img).convert("RGB")
            if st.button("🔍 OCRで読み取る", type="primary"):
                with st.spinner("読み取り中..."):
                    try:
                        from ocr_gcv import image_to_text
                        st.session_state["ocr_raw"] = image_to_text(pil_img, api_key)
                    except Exception as e:
                        st.error(f"OCRエラー: {e}")

    if "ocr_raw" in st.session_state:
        st.divider()
        ocr_col, form_col = st.columns([1, 1], gap="large")

        with ocr_col:
            st.markdown("**📄 OCRテキスト**")
            st.caption("テキストを選択してコピーし、右の入力欄に貼り付けてください")
            st.text_area("", value=st.session_state["ocr_raw"], height=600,
                         label_visibility="collapsed", key="ocr_text_display")
            if st.button("🔄 OCR結果をクリア", use_container_width=True):
                del st.session_state["ocr_raw"]
                st.rerun()

        with form_col:
            st.markdown("**➕ 設問をまとめて入力して追加**")
            st.caption("項目は1行1つ。人数はあとで「データ入力」タブから入力できます。")

            if "ocr_slot_count" not in st.session_state:
                st.session_state.ocr_slot_count = 1

            # 過去の設問から一括追加
            if st.session_state.past_sections:
                with st.expander("💡 過去の設問から追加", expanded=False):
                    past_titles = [s["title"] for s in st.session_state.past_sections]
                    ocr_multi = st.multiselect("設問を選択", past_titles, key="ocr_past_multi", label_visibility="collapsed")
                    if st.button("選択した設問を一括追加", key="ocr_bulk_add", use_container_width=True) and ocr_multi:
                        for title in ocr_multi:
                            t = next(s for s in st.session_state.past_sections if s["title"] == title)
                            items = [{"label": it["label"], "count": 0} for it in t["items"]]
                            st.session_state.sections.append({"title": t["title"], "note": t["note"], "items": items})
                        save_to_storage(None)
                        st.toast(f"{len(ocr_multi)}件の設問を追加しました ✅")
                        st.rerun()

            st.divider()

            # 複数スロット入力
            ocr_slots = []
            for i in range(st.session_state.ocr_slot_count):
                if i > 0:
                    st.markdown("---")
                st.markdown(f"**設問 {i+1}**")
                t = st.text_input("設問タイトル", key=f"ocr_st_{i}", placeholder="例）問1. 性別を教えてください")
                n = st.text_input("補足メモ（任意）", key=f"ocr_sn_{i}", placeholder="例）※複数回答可")
                it = st.text_area("回答項目（1行1項目）", key=f"ocr_si_{i}", height=100,
                                  placeholder="はい\nいいえ\nわからない")
                ocr_slots.append({"title": t, "note": n, "items_text": it})

            col_sl, col_sa = st.columns([1, 2])
            if col_sl.button("＋ 設問を追加", key="ocr_add_slot", use_container_width=True):
                st.session_state.ocr_slot_count += 1
                st.rerun()

            if col_sa.button("✅ すべて追加", key="ocr_submit_all", type="primary", use_container_width=True):
                added = 0
                errors = []
                for i, slot in enumerate(ocr_slots):
                    if not slot["title"].strip():
                        continue
                    lines = [l.strip() for l in slot["items_text"].splitlines() if l.strip()]
                    if not lines:
                        errors.append(f"設問{i+1}：項目が未入力です")
                        continue
                    new_s = {"title": slot["title"], "note": slot["note"],
                             "items": [{"label": l, "count": 0} for l in lines]}
                    st.session_state.sections.append(new_s)
                    _merge_past_sections(new_s)
                    added += 1
                if errors:
                    for e in errors:
                        st.error(e)
                if added:
                    save_to_storage(None)
                    st.session_state.ocr_slot_count = 1
                    for k in list(st.session_state.keys()):
                        if k.startswith("ocr_st_") or k.startswith("ocr_sn_") or k.startswith("ocr_si_"):
                            del st.session_state[k]
                    st.toast(f"{added}件の設問を追加しました ✅")
                    st.rerun()

# ══════════════════════════════════════════════
# タブ1：データ入力
# ══════════════════════════════════════════════
with tab_input:
    col_left, col_right = st.columns([1, 1], gap="large")

    # ── 左カラム：新規設問追加 ──────────────────
    with col_left:
        st.subheader("➕ 設問を追加")

        q_title = st.text_input("設問タイトル", placeholder="例）問1. 性別を教えてください", key="tab_q_title")
        q_note  = st.text_input("補足メモ（任意）", placeholder="例）※複数回答可", key="tab_q_note")

        st.markdown("**回答項目と人数**")
        st.caption("空行は無視されます")

        if "row_count" not in st.session_state:
            st.session_state.row_count = 4

        rows = []
        for i in range(st.session_state.row_count):
            c1, c2 = st.columns([3, 1])
            label = c1.text_input(f"項目{i+1}", key=f"label_{i}", label_visibility="collapsed",
                                   placeholder=f"項目{i+1}")
            count = c2.number_input("人数", min_value=0, value=0, key=f"count_{i}",
                                     label_visibility="collapsed")
            rows.append({"label": label, "count": count})

        col_add, col_clear = st.columns(2)
        if col_add.button("＋ 行を追加"):
            st.session_state.row_count += 2
            st.rerun()
        if col_clear.button("行数をリセット"):
            st.session_state.row_count = 4
            st.rerun()

        # 過去の設問からサジェスト
        if st.session_state.past_sections:
            with st.expander("💡 過去の設問から追加", expanded=False):
                past_titles = [s["title"] for s in st.session_state.past_sections]
                tab_multi = st.multiselect("設問を選択", past_titles, key="tab_past_multi", label_visibility="collapsed")
                c1, c2 = st.columns(2)
                if c1.button("一括追加（人数は後で入力）", key="tab_bulk_add") and tab_multi:
                    for title in tab_multi:
                        t = next(s for s in st.session_state.past_sections if s["title"] == title)
                        items = [{"label": it["label"], "count": 0} for it in t["items"]]
                        new_s = {"title": t["title"], "note": t["note"], "items": items}
                        st.session_state.sections.append(new_s)
                    save_to_storage(None)
                    st.toast(f"{len(tab_multi)}件の設問を追加しました ✅")
                    st.rerun()
                if c2.button("フォームに入力（1件）", key="tab_apply_past") and tab_multi:
                    target = next(s for s in st.session_state.past_sections if s["title"] == tab_multi[0])
                    st.session_state["tab_pending_fill"] = target
                    st.rerun()

        if st.button("✅ この設問を追加", type="primary", use_container_width=True):
            valid_rows = [r for r in rows if r["label"].strip()]
            if not q_title.strip():
                st.error("設問タイトルを入力してください")
            elif not valid_rows:
                st.error("1件以上の回答項目を入力してください")
            else:
                new_sec = {"title": q_title, "note": q_note, "items": valid_rows}
                st.session_state.sections.append(new_sec)
                save_to_storage(new_sec)
                st.session_state.row_count = 4
                for k in list(st.session_state.keys()):
                    if k.startswith("label_") or k.startswith("count_"):
                        del st.session_state[k]
                for k in ["tab_q_title", "tab_q_note"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.toast(f"「{q_title}」を追加しました ✅")
                st.rerun()

    # ── 右カラム：登録済み設問リスト ───────────
    with col_right:
        st.subheader("📋 登録済み設問一覧")

        if not st.session_state.sections:
            st.info("まだ設問が追加されていません")
        else:
            for idx, sec in enumerate(st.session_state.sections):
                total = sum(int(r["count"]) for r in sec["items"])
                with st.expander(f"Q{idx+1}. {sec['title']}　（合計 {total}人）", expanded=False):

                    # 人数編集フォーム
                    new_counts = []
                    for j, row in enumerate(sec["items"]):
                        if not row["label"].strip():
                            continue
                        c1, c2 = st.columns([3, 1])
                        c1.markdown(f"**{row['label']}**")
                        new_cnt = c2.number_input("人数", min_value=0,
                                                   value=int(row["count"]),
                                                   key=f"edit_count_{idx}_{j}",
                                                   label_visibility="collapsed")
                        new_counts.append((j, new_cnt))

                    new_comment = st.text_area(
                        "コメント（任意）",
                        value=sec.get("comment", ""),
                        key=f"edit_comment_{idx}",
                        placeholder="この設問に対するコメントや考察を入力（PDF・プレビューに反映されます）",
                        height=80,
                    )

                    if st.button("💾 保存", key=f"save_{idx}", use_container_width=True):
                        for j, cnt in new_counts:
                            st.session_state.sections[idx]["items"][j]["count"] = cnt
                        st.session_state.sections[idx]["comment"] = new_comment
                        save_to_storage()
                        st.toast("保存しました ✅")
                        st.rerun()

                    st.divider()
                    col_up, col_dn, col_del = st.columns(3)
                    if col_up.button("↑ 上へ", key=f"up_{idx}") and idx > 0:
                        s = st.session_state.sections
                        s[idx], s[idx-1] = s[idx-1], s[idx]
                        save_to_storage()
                        st.rerun()
                    if col_dn.button("↓ 下へ", key=f"dn_{idx}") and idx < len(st.session_state.sections)-1:
                        s = st.session_state.sections
                        s[idx], s[idx+1] = s[idx+1], s[idx]
                        save_to_storage()
                        st.rerun()
                    if col_del.button("🗑️ 削除", key=f"del_{idx}"):
                        st.session_state.sections.pop(idx)
                        save_to_storage()
                        st.rerun()

            st.divider()
            if st.button("🗑️ 全設問を削除", use_container_width=True, type="secondary"):
                st.session_state.sections = []
                clear_storage()
                st.rerun()

# ══════════════════════════════════════════════
# タブ2：プレビュー
# ══════════════════════════════════════════════
with tab_preview:
    st.subheader("📊 データプレビュー")

    if not st.session_state.sections:
        st.info("「データ入力」タブで設問を追加してください")
    else:
        if base_value is not None:
            base = base_value
        else:
            base = calc_base(st.session_state.sections)

        st.caption(f"集計ベース: **{base}人**　グラフ種類: **{graph_type}**")

        for idx, sec in enumerate(st.session_state.sections):
            st.markdown(f"#### Q{idx+1}. {sec['title']}")
            if sec.get("note"):
                st.caption(sec["note"])

            items = [(r["label"], int(r["count"])) for r in sec["items"] if r["label"].strip()]
            if not items:
                continue

            import pandas as pd
            df = pd.DataFrame(items, columns=["項目", "人数"])
            df["割合（%）"] = df["人数"].apply(lambda x: f"{x/base*100:.1f}%")
            st.dataframe(df, use_container_width=True, hide_index=True)

            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.font_manager as fm

            fp = fm.FontProperties(fname="fonts/NotoSansJP-Regular.ttf")
            n = len(items)

            if graph_type == "縦棒グラフ":
                rotation = 0 if n <= 6 else (45 if n <= 12 else 90)
                ha       = "center" if rotation == 0 else "right"
                lbl_fs   = max(6, 8 - max(0, n - 6) // 3)
                fig, ax = plt.subplots(figsize=(max(8, n * 1.0), 4))
                labels = [l for l, _ in items]
                counts = [c for _, c in items]
                bars = ax.bar(range(n), counts, color="#3a7ebf")
                for bar, cnt in zip(bars, counts):
                    if cnt > 0:
                        pct = cnt / base * 100
                        ax.text(bar.get_x() + bar.get_width() / 2,
                                bar.get_height() + max(counts) * 0.01,
                                f"{cnt}\n({pct:.1f}%)",
                                ha="center", va="bottom",
                                fontsize=max(5, lbl_fs - 1), fontproperties=fp)
                ax.set_xticks(range(n))
                ax.set_xticklabels(labels, fontproperties=fp, fontsize=lbl_fs,
                                   rotation=rotation, ha=ha)
                for lbl in ax.get_yticklabels():
                    lbl.set_fontproperties(fp)
                if max(counts, default=0) > 0:
                    ax.set_ylim(0, max(counts) * 1.35)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

            elif graph_type == "円グラフ":
                filtered = [(l, c) for l, c in items if c > 0]
                if filtered:
                    fig, ax = plt.subplots(figsize=(8, 4))
                    lf = [l for l, _ in filtered]
                    cf = [c for _, c in filtered]
                    pf = [c / base * 100 for c in cf]
                    wedges, _ = ax.pie(cf, labels=None, startangle=90,
                                       counterclock=False,
                                       wedgeprops={"linewidth": 0.8, "edgecolor": "white"})
                    legend_labels = [f"{l}  {c}人 ({p:.1f}%)"
                                     for l, c, p in zip(lf, cf, pf)]
                    ax.legend(wedges, legend_labels, loc="center left",
                              bbox_to_anchor=(1.0, 0.5), fontsize=8, prop=fp, frameon=False)
                    ax.set_aspect("equal")
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)

            elif graph_type == "横棒グラフ":
                lbl_fs = max(6, 8 - max(0, n - 10) // 3)
                fig, ax = plt.subplots(figsize=(8, max(2.5, n * 0.5)))
                labels = [l for l, _ in items]
                counts = [c for _, c in items]
                bars = ax.barh(range(n), counts, color="#3a7ebf")
                for bar, cnt in zip(bars, counts):
                    if cnt > 0:
                        pct = cnt / base * 100
                        ax.text(bar.get_width() + max(counts) * 0.01,
                                bar.get_y() + bar.get_height() / 2,
                                f"{cnt} ({pct:.1f}%)",
                                ha="left", va="center",
                                fontsize=lbl_fs, fontproperties=fp)
                ax.set_yticks(range(n))
                ax.set_yticklabels(labels, fontproperties=fp, fontsize=lbl_fs)
                for lbl in ax.get_xticklabels():
                    lbl.set_fontproperties(fp)
                if max(counts, default=0) > 0:
                    ax.set_xlim(0, max(counts) * 1.45)
                ax.invert_yaxis()
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

            if sec.get("comment"):
                st.info(sec["comment"].replace("\n", "  \n"))

            st.divider()

# ══════════════════════════════════════════════
# タブ3：PDF出力
# ══════════════════════════════════════════════
with tab_export:
    st.subheader("📄 PDFレポートを生成・ダウンロード")

    if not st.session_state.sections:
        st.info("「データ入力」タブで設問を追加してください")
    else:
        if base_value is not None:
            base = base_value
        else:
            base = calc_base(st.session_state.sections)

        st.markdown(f"""
        | 設定項目 | 内容 |
        |---|---|
        | レポートタイトル | {report_title} |
        | 集計ベース | {base}人 |
        | グラフ種類 | {graph_type} |
        | 設問数 | {len(st.session_state.sections)}問 |
        """)

        col1, col2, col3 = st.columns(3)

        for gtype, col, fname in [
            ("縦棒グラフ", col1, "report_bar.pdf"),
            ("円グラフ",   col2, "report_pie.pdf"),
            ("横棒グラフ", col3, "report_hbar.pdf"),
        ]:
            with col:
                if st.button(f"📊 {gtype}版を生成", use_container_width=True):
                    with st.spinner(f"{gtype}版PDFを生成中..."):
                        try:
                            sections_fmt = sections_to_pdf_format(st.session_state.sections)
                            pdf_bytes = generate_pdf(
                                sections=sections_fmt,
                                base=base,
                                report_title=report_title,
                                graph_type=gtype,
                            )
                            st.session_state[f"pdf_{gtype}"] = (pdf_bytes, fname)
                            st.success("生成完了！")
                        except Exception as e:
                            st.error(f"エラー: {e}")

                if f"pdf_{gtype}" in st.session_state:
                    pdf_bytes, fname = st.session_state[f"pdf_{gtype}"]
                    st.download_button(
                        f"⬇️ {fname} をダウンロード",
                        data=pdf_bytes,
                        file_name=fname,
                        mime="application/pdf",
                        use_container_width=True,
                    )

        st.divider()
        st.markdown("### 📦 全グラフをまとめて生成")
        if st.button("3種類すべてを一括生成", use_container_width=True, type="primary"):
            sections_fmt = sections_to_pdf_format(st.session_state.sections)
            errors = []
            for gtype, fname in [
                ("縦棒グラフ", "report_bar.pdf"),
                ("円グラフ",   "report_pie.pdf"),
                ("横棒グラフ", "report_hbar.pdf"),
            ]:
                with st.spinner(f"{gtype}版を生成中..."):
                    try:
                        pdf_bytes = generate_pdf(
                            sections=sections_fmt,
                            base=base,
                            report_title=report_title,
                            graph_type=gtype,
                        )
                        st.session_state[f"pdf_{gtype}"] = (pdf_bytes, fname)
                    except Exception as e:
                        errors.append(f"{gtype}: {e}")
            if errors:
                st.error("\n".join(errors))
            else:
                st.success("3種類すべて生成しました。上のボタンからダウンロードできます。")
                st.rerun()
