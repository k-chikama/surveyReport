# -*- coding: utf-8 -*-
"""
アンケート集計レポート自動生成システム
Streamlit Web アプリ（手動入力版）

起動方法:
  streamlit run app.py
"""

import streamlit as st
import json
import os

from pdf_generator import generate_pdf
from ocr_gcv import is_gcv_available, image_to_questions

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
# セッション状態の初期化
# ─────────────────────────────────────────────
if "sections" not in st.session_state:
    st.session_state.sections = []   # [{title, note, items:[{label,count}]}, ...]

if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

# ─────────────────────────────────────────────
# ヘルパー
# ─────────────────────────────────────────────
def sections_to_pdf_format(sections_state):
    """セッション状態 → pdf_generator 用フォーマット"""
    result = []
    for sec in sections_state:
        items = [(row["label"], int(row["count"])) for row in sec["items"] if row["label"].strip()]
        result.append({
            "title": sec["title"],
            "note":  sec.get("note", ""),
            "items": items,
        })
    return result

def calc_base(sections_state):
    """最大人数合計をベースとして算出（最初の単一回答設問を優先）"""
    for sec in sections_state:
        total = sum(int(r["count"]) for r in sec["items"] if r["label"].strip())
        if total > 0:
            return total
    return 1

# ─────────────────────────────────────────────
# サイドバー：レポート設定
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ レポート設定")

    report_title = st.text_input(
        "レポートタイトル",
        value="アンケート調査結果報告書",
    )

    base_mode = st.radio(
        "集計ベース（分母）",
        ["自動（最初の設問の合計）", "手動で指定"],
        index=0,
    )
    if base_mode == "手動で指定":
        base_value = st.number_input("集計ベース人数", min_value=1, value=290, step=1)
    else:
        base_value = None

    graph_type = st.selectbox(
        "グラフ種類",
        ["縦棒グラフ", "円グラフ", "横棒グラフ"],
        index=0,
    )

    st.divider()
    st.markdown("### 💾 データ管理")

    # JSON エクスポート
    if st.session_state.sections:
        json_str = json.dumps(st.session_state.sections, ensure_ascii=False, indent=2)
        st.download_button(
            "📥 データをJSONで保存",
            data=json_str.encode("utf-8"),
            file_name="survey_data.json",
            mime="application/json",
        )

    # JSON インポート
    uploaded_json = st.file_uploader("📤 JSONデータを読み込む", type=["json"])
    if uploaded_json:
        try:
            loaded = json.loads(uploaded_json.read().decode("utf-8"))
            st.session_state.sections = loaded
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
            st.image(pil_img, caption="アップロード画像", use_container_width=True)

            if st.button("🔍 OCRで読み取る", type="primary"):
                with st.spinner("読み取り中..."):
                    try:
                        questions, raw_text = image_to_questions(pil_img, api_key)
                        st.session_state["ocr_questions"] = questions
                        st.session_state["ocr_raw"] = raw_text
                    except Exception as e:
                        st.error(f"OCRエラー: {e}")

        if "ocr_questions" in st.session_state:
            st.divider()
            with st.expander("📄 OCR生テキスト", expanded=False):
                st.text(st.session_state["ocr_raw"])

            questions = st.session_state["ocr_questions"]
            if not questions:
                st.warning("設問構造を自動検出できませんでした。生テキストを確認して手動入力してください。")
            else:
                st.markdown(f"**{len(questions)}件の設問を検出しました。** 追加したい設問を選んでください。")
                selected = []
                for i, q in enumerate(questions):
                    checked = st.checkbox(f"Q{i+1}. {q.title}", value=True, key=f"ocr_chk_{i}")
                    if checked:
                        st.caption(f"選択肢: {', '.join(q.choices) if q.choices else '（なし）'}")
                        selected.append(q)

                if st.button("✅ 選択した設問を追加（人数は後で入力）", type="primary", use_container_width=True):
                    for q in selected:
                        items = [{"label": c, "count": 0} for c in q.choices] if q.choices else [{"label": "", "count": 0}]
                        st.session_state.sections.append({
                            "title": q.title,
                            "note": q.note,
                            "items": items,
                        })
                    del st.session_state["ocr_questions"]
                    del st.session_state["ocr_raw"]
                    st.success(f"{len(selected)}件の設問を追加しました。「データ入力」タブで人数を入力してください。")
                    st.rerun()

# ══════════════════════════════════════════════
# タブ1：データ入力
# ══════════════════════════════════════════════
with tab_input:
    col_left, col_right = st.columns([1, 1], gap="large")

    # ── 左カラム：新規設問追加 ──────────────────
    with col_left:
        st.subheader("➕ 設問を追加")

        q_title = st.text_input("設問タイトル", placeholder="例）問1. 性別を教えてください")
        q_note  = st.text_input("補足メモ（任意）", placeholder="例）※複数回答可")

        st.markdown("**回答項目と人数**")
        st.caption("空行は無視されます")

        # 動的行追加
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

        if st.button("✅ この設問を追加", type="primary", use_container_width=True):
            valid_rows = [r for r in rows if r["label"].strip()]
            if not q_title.strip():
                st.error("設問タイトルを入力してください")
            elif not valid_rows:
                st.error("1件以上の回答項目を入力してください")
            else:
                st.session_state.sections.append({
                    "title": q_title,
                    "note":  q_note,
                    "items": valid_rows,
                })
                # 入力欄リセット
                st.session_state.row_count = 4
                for i in range(20):
                    for key in [f"label_{i}", f"count_{i}"]:
                        if key in st.session_state:
                            del st.session_state[key]
                st.success(f"「{q_title}」を追加しました")
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

                    # 簡易テーブル表示
                    for row in sec["items"]:
                        if row["label"].strip():
                            pct = int(row["count"]) / total * 100 if total > 0 else 0
                            st.write(f"- **{row['label']}**: {row['count']}人 ({pct:.1f}%)")

                    col_up, col_dn, col_del = st.columns(3)
                    if col_up.button("↑ 上へ", key=f"up_{idx}") and idx > 0:
                        s = st.session_state.sections
                        s[idx], s[idx-1] = s[idx-1], s[idx]
                        st.rerun()
                    if col_dn.button("↓ 下へ", key=f"dn_{idx}") and idx < len(st.session_state.sections)-1:
                        s = st.session_state.sections
                        s[idx], s[idx+1] = s[idx+1], s[idx]
                        st.rerun()
                    if col_del.button("🗑️ 削除", key=f"del_{idx}"):
                        st.session_state.sections.pop(idx)
                        st.rerun()

            if st.button("🗑️ 全設問を削除", use_container_width=True):
                st.session_state.sections = []
                st.rerun()

# ══════════════════════════════════════════════
# タブ2：プレビュー
# ══════════════════════════════════════════════
with tab_preview:
    st.subheader("📊 データプレビュー")

    if not st.session_state.sections:
        st.info("「データ入力」タブで設問を追加してください")
    else:
        # ベース計算
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

            # テーブル
            import pandas as pd
            df = pd.DataFrame(items, columns=["項目", "人数"])
            df["割合（%）"] = df["人数"].apply(lambda x: f"{x/base*100:.1f}%")
            st.dataframe(df, use_container_width=True, hide_index=True)

            # グラフプレビュー（matplotlib）
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
