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

st.title("📊 アンケート集計レポート生成システム")
st.caption("質問と集計データを入力して、印刷用PDFレポートを自動生成します。")

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
        if _saved:
            try:
                _data = json.loads(_saved)
                st.session_state.sections = _data.get("sections", [])
                st.session_state.past_sections = _data.get("past_sections", [])
            except Exception:
                pass
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

    uploaded_json = st.file_uploader("📤 JSONデータを読み込む", type=["json"])
    if uploaded_json:
        try:
            loaded = json.loads(uploaded_json.read().decode("utf-8"))
            st.session_state.sections = loaded
            save_to_storage(None)
            st.success("データを読み込みました")
            st.rerun()
        except Exception as e:
            st.error(f"読み込みエラー: {e}")

# ─────────────────────────────────────────────
# メインエリア：タブ構成
# ─────────────────────────────────────────────
tab_ocr, tab_input, tab_preview, tab_export = st.tabs(["📷 OCR読み取り", "📝 データ入力", "👁️ プレビュー", "📄 PDF出力"])

# ══════════════════════════════════════════════
# タブ0：OCR読み取り
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
                with st.expander(f"Q{idx+1}. {sec['title']}", expanded=False):
                    total = sum(int(r["count"]) for r in sec["items"])
                    st.caption(f"回答合計: {total}人  |  項目数: {len(sec['items'])}件")

                    for row in sec["items"]:
                        if row["label"].strip():
                            pct = int(row["count"]) / total * 100 if total > 0 else 0
                            st.write(f"- **{row['label']}**: {row['count']}人 ({pct:.1f}%)")

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

            if graph_type == "縦棒グラフ":
                fig, ax = plt.subplots(figsize=(8, 3.5))
                labels = [l for l, _ in items]
                counts = [c for _, c in items]
                ax.bar(range(len(items)), counts, color="#3a7ebf")
                ax.set_xticks(range(len(items)))
                ax.set_xticklabels(labels, fontproperties=fp, fontsize=8)
                for lbl in ax.get_yticklabels():
                    lbl.set_fontproperties(fp)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

            elif graph_type == "円グラフ":
                filtered = [(l, c) for l, c in items if c > 0]
                if filtered:
                    fig, ax = plt.subplots(figsize=(7, 4))
                    labels_f = [l for l, _ in filtered]
                    counts_f = [c for _, c in filtered]
                    wedges, texts, autotexts = ax.pie(
                        counts_f,
                        labels=labels_f,
                        autopct="%1.1f%%",
                        startangle=90,
                        counterclock=False,
                        textprops={"fontproperties": fp, "fontsize": 8},
                    )
                    for at in autotexts:
                        at.set_fontproperties(fp)
                    ax.set_aspect("equal")
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)

            elif graph_type == "横棒グラフ":
                fig, ax = plt.subplots(figsize=(8, max(2.5, len(items) * 0.45)))
                labels = [l for l, _ in items]
                counts = [c for _, c in items]
                ax.barh(range(len(items)), counts, color="#3a7ebf")
                ax.set_yticks(range(len(items)))
                ax.set_yticklabels(labels, fontproperties=fp, fontsize=8)
                for lbl in ax.get_xticklabels():
                    lbl.set_fontproperties(fp)
                ax.invert_yaxis()
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

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
