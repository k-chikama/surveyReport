# -*- coding: utf-8 -*-
"""
縦棒グラフ版 PDF レポート生成
出力: output/report_bar.pdf
"""

import os
import sys
import io
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from data import SECTIONS, BASE

# ─────────────────────────────────────────────
# フォント設定（フォールバック禁止）
# ─────────────────────────────────────────────
FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansJP-Regular.ttf")

if not os.path.exists(FONT_PATH):
    print(f"[ERROR] フォントファイルが見つかりません: {FONT_PATH}", file=sys.stderr)
    sys.exit(1)

# reportlab 用フォント登録
pdfmetrics.registerFont(TTFont("NotoSansJP", FONT_PATH))
RL_FONT = "NotoSansJP"

# matplotlib 用フォント設定
_fp = fm.FontProperties(fname=FONT_PATH)
plt.rcParams["font.family"] = _fp.get_name()
# フォールバック候補を空にして他フォントへの逃げを防ぐ
plt.rcParams["font.sans-serif"] = [_fp.get_name()]
plt.rcParams["axes.unicode_minus"] = False

# ─────────────────────────────────────────────
# ページ設定
# ─────────────────────────────────────────────
PAGE_W, PAGE_H = A4          # 595.28 x 841.89 pt
MARGIN_LR = 20 * mm
MARGIN_TB = 20 * mm
CONTENT_W = PAGE_W - MARGIN_LR * 2   # 約 155mm

# ─────────────────────────────────────────────
# reportlab スタイル定義
# ─────────────────────────────────────────────
def make_styles():
    title_style = ParagraphStyle(
        "ReportTitle",
        fontName=RL_FONT,
        fontSize=16,
        leading=22,
        alignment=1,   # center
        spaceAfter=6 * mm,
    )
    section_style = ParagraphStyle(
        "SectionTitle",
        fontName=RL_FONT,
        fontSize=11,
        leading=16,
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
        textColor=colors.HexColor("#1a3c5e"),
    )
    note_style = ParagraphStyle(
        "Note",
        fontName=RL_FONT,
        fontSize=8,
        leading=12,
        textColor=colors.grey,
        spaceAfter=1 * mm,
    )
    return title_style, section_style, note_style

# ─────────────────────────────────────────────
# 集計テーブル生成
# ─────────────────────────────────────────────
BAR_COLOR = "#3a7ebf"

def make_table(items, base):
    """reportlab Table を返す"""
    col_widths = [CONTENT_W * 0.55, CONTENT_W * 0.20, CONTENT_W * 0.25]

    header_style = ParagraphStyle(
        "TH", fontName=RL_FONT, fontSize=9, leading=13,
        alignment=1, textColor=colors.white,
    )
    cell_style_left = ParagraphStyle(
        "TD_L", fontName=RL_FONT, fontSize=9, leading=13,
    )
    cell_style_right = ParagraphStyle(
        "TD_R", fontName=RL_FONT, fontSize=9, leading=13,
        alignment=2,
    )

    data = [
        [
            Paragraph("項目", header_style),
            Paragraph("人数", header_style),
            Paragraph("割合（％）", header_style),
        ]
    ]
    for label, count in items:
        pct = count / base * 100
        data.append([
            Paragraph(label, cell_style_left),
            Paragraph(str(count), cell_style_right),
            Paragraph(f"{pct:.1f}%", cell_style_right),
        ])

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3c5e")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, -1), RL_FONT),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f0f5fb")]),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
    ]))
    return tbl


# ─────────────────────────────────────────────
# 縦棒グラフ生成 → PNG bytes
# ─────────────────────────────────────────────
MAX_LABEL_CHARS = 6   # 1行あたり最大文字数（折り返し基準）

def wrap_label(text, max_chars=MAX_LABEL_CHARS):
    """長いラベルを改行する"""
    lines = textwrap.wrap(text, width=max_chars, break_long_words=True)
    return "\n".join(lines) if lines else text

def make_bar_chart(items, base, title):
    """縦棒グラフを描いて PNG bytes を返す"""
    labels = [wrap_label(label) for label, _ in items]
    counts = [count for _, count in items]
    pcts   = [count / base * 100 for count in counts]

    n = len(items)
    # 項目数に応じて図の幅を調整（最低 10cm）
    fig_w = max(10, n * 1.4)
    fig_h = 5.5

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor("white")

    x = range(n)
    bars = ax.bar(x, counts, color=BAR_COLOR, width=0.55, zorder=2)

    # 棒の上に「人数＋％」表示
    for bar, count, pct in zip(bars, counts, pcts):
        if count == 0:
            continue
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(counts) * 0.01,
            f"{count}人\n({pct:.1f}%)",
            ha="center", va="bottom",
            fontsize=8,
            fontproperties=fm.FontProperties(fname=FONT_PATH),
        )

    ax.set_xticks(list(x))
    ax.set_xticklabels(
        labels, fontproperties=fm.FontProperties(fname=FONT_PATH), fontsize=9
    )
    ax.yaxis.set_tick_params(labelsize=8)
    for label in ax.get_yticklabels():
        label.set_fontproperties(fm.FontProperties(fname=FONT_PATH))

    ax.set_ylabel(
        "人数（人）",
        fontproperties=fm.FontProperties(fname=FONT_PATH),
        fontsize=9,
    )
    ax.yaxis.grid(True, linestyle="--", alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # y軸上限に余白
    if max(counts) > 0:
        ax.set_ylim(0, max(counts) * 1.25)

    plt.tight_layout(pad=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────
# ブロック（表＋グラフ）を KeepTogether で組む
# ─────────────────────────────────────────────
def make_block(section, title_style, section_style, note_style):
    """1設問分の Flowable リストを返す（KeepTogether で包む）"""
    items = section["items"]
    base  = BASE

    # 設問タイトル
    heading = Paragraph(section["title"], section_style)

    flowables_inner = []

    # 注記
    if section.get("note"):
        flowables_inner.append(Paragraph(section["note"], note_style))

    # 表
    tbl = make_table(items, base)
    flowables_inner.append(tbl)
    flowables_inner.append(Spacer(1, 3 * mm))

    # 縦棒グラフ
    buf = make_bar_chart(items, base, section["title"])
    img = RLImage(buf, width=CONTENT_W, height=CONTENT_W * 0.45)
    flowables_inner.append(img)

    return KeepTogether([heading] + flowables_inner)


# ─────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────
def build_pdf():
    out_path = os.path.join(os.path.dirname(__file__), "output", "report_bar.pdf")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=MARGIN_LR,
        rightMargin=MARGIN_LR,
        topMargin=MARGIN_TB,
        bottomMargin=MARGIN_TB,
    )

    title_style, section_style, note_style = make_styles()

    story = []

    # ── 表紙タイトル ──
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("物価高の影響についての意識調査結果報告書", title_style))
    story.append(Paragraph(f"集計ベース：{BASE}人", ParagraphStyle(
        "sub", fontName=RL_FONT, fontSize=10, alignment=1, spaceAfter=8 * mm,
        textColor=colors.grey,
    )))
    story.append(Spacer(1, 4 * mm))

    # ── 各設問ブロック ──
    for section in SECTIONS:
        block = make_block(section, title_style, section_style, note_style)
        story.append(block)
        story.append(Spacer(1, 6 * mm))

    doc.build(story)
    print(f"[OK] 生成完了: {out_path}")


if __name__ == "__main__":
    build_pdf()
