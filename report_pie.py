# -*- coding: utf-8 -*-
"""
円グラフ版 PDF レポート生成
出力: output/report_pie.pdf
"""

import os
import sys
import io

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

pdfmetrics.registerFont(TTFont("NotoSansJP", FONT_PATH))
RL_FONT = "NotoSansJP"

_fp = fm.FontProperties(fname=FONT_PATH)
plt.rcParams["font.family"] = _fp.get_name()
plt.rcParams["font.sans-serif"] = [_fp.get_name()]
plt.rcParams["axes.unicode_minus"] = False

# ─────────────────────────────────────────────
# ページ設定
# ─────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN_LR = 20 * mm
MARGIN_TB = 20 * mm
CONTENT_W = PAGE_W - MARGIN_LR * 2

# ─────────────────────────────────────────────
# カラーパレット（最大11色）
# ─────────────────────────────────────────────
PIE_COLORS = [
    "#3a7ebf", "#e07b39", "#4caf50", "#9c27b0", "#f44336",
    "#00bcd4", "#ff9800", "#607d8b", "#8bc34a", "#e91e63", "#795548",
]

# ─────────────────────────────────────────────
# スタイル定義
# ─────────────────────────────────────────────
def make_styles():
    title_style = ParagraphStyle(
        "ReportTitle",
        fontName=RL_FONT,
        fontSize=16,
        leading=22,
        alignment=1,
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
def make_table(items, base):
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
# 円グラフ生成 → PNG bytes
# ─────────────────────────────────────────────
def make_pie_chart(items, base):
    """円グラフを描いて PNG bytes を返す。0件はスキップ。"""
    fp = fm.FontProperties(fname=FONT_PATH)

    # 0件除外
    filtered = [(label, count) for label, count in items if count > 0]
    if not filtered:
        return None

    labels_raw = [label for label, _ in filtered]
    counts     = [count for _, count in filtered]
    pcts       = [count / base * 100 for count in counts]
    pie_colors = PIE_COLORS[:len(filtered)]

    # ラベル文字列：「項目\n人数人 (XX.X%)」
    pie_labels = [
        f"{lbl}\n{cnt}人 ({pct:.1f}%)"
        for lbl, cnt, pct in zip(labels_raw, counts, pcts)
    ]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    fig.patch.set_facecolor("white")

    wedges, texts = ax.pie(
        counts,
        labels=None,          # ラベルは legend で表示
        colors=pie_colors,
        startangle=90,
        counterclock=False,
        wedgeprops={"linewidth": 0.8, "edgecolor": "white"},
        pctdistance=0.75,
    )

    # 凡例：「項目 人数人 (XX.X%)」
    legend_labels = [
        f"{lbl}  {cnt}人  ({pct:.1f}%)"
        for lbl, cnt, pct in zip(labels_raw, counts, pcts)
    ]
    ax.legend(
        wedges,
        legend_labels,
        loc="center left",
        bbox_to_anchor=(1.0, 0.5),
        fontsize=8,
        prop=fp,
        frameon=False,
    )

    ax.set_aspect("equal")
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
    items = section["items"]
    base  = BASE

    heading = Paragraph(section["title"], section_style)
    flowables_inner = []

    if section.get("note"):
        flowables_inner.append(Paragraph(section["note"], note_style))

    # 表
    tbl = make_table(items, base)
    flowables_inner.append(tbl)
    flowables_inner.append(Spacer(1, 3 * mm))

    # 円グラフ
    buf = make_pie_chart(items, base)
    if buf:
        img = RLImage(buf, width=CONTENT_W, height=CONTENT_W * 0.42)
        flowables_inner.append(img)

    return KeepTogether([heading] + flowables_inner)


# ─────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────
def build_pdf():
    out_path = os.path.join(os.path.dirname(__file__), "output", "report_pie.pdf")
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

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("物価高の影響についての意識調査結果報告書", title_style))
    story.append(Paragraph(f"集計ベース：{BASE}人", ParagraphStyle(
        "sub", fontName=RL_FONT, fontSize=10, alignment=1, spaceAfter=8 * mm,
        textColor=colors.grey,
    )))
    story.append(Spacer(1, 4 * mm))

    for section in SECTIONS:
        block = make_block(section, title_style, section_style, note_style)
        story.append(block)
        story.append(Spacer(1, 6 * mm))

    doc.build(story)
    print(f"[OK] 生成完了: {out_path}")


if __name__ == "__main__":
    build_pdf()
