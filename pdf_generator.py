# -*- coding: utf-8 -*-
"""
PDF生成モジュール
縦棒グラフ / 円グラフ / 横棒グラフ の3種対応
"""

import os
import io
import sys
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

BAR_COLOR = "#3a7ebf"
PIE_COLORS = [
    "#3a7ebf", "#e07b39", "#4caf50", "#9c27b0", "#f44336",
    "#00bcd4", "#ff9800", "#607d8b", "#8bc34a", "#e91e63", "#795548",
]

# ─────────────────────────────────────────────
# スタイル定義
# ─────────────────────────────────────────────
def _make_styles():
    title_style = ParagraphStyle(
        "ReportTitle", fontName=RL_FONT, fontSize=16, leading=22,
        alignment=1, spaceAfter=4 * mm,
    )
    sub_style = ParagraphStyle(
        "SubTitle", fontName=RL_FONT, fontSize=10, leading=14,
        alignment=1, spaceAfter=6 * mm, textColor=colors.grey,
    )
    section_style = ParagraphStyle(
        "SectionTitle", fontName=RL_FONT, fontSize=11, leading=16,
        spaceBefore=4 * mm, spaceAfter=2 * mm,
        textColor=colors.HexColor("#1a3c5e"),
    )
    note_style = ParagraphStyle(
        "Note", fontName=RL_FONT, fontSize=8, leading=12,
        textColor=colors.grey, spaceAfter=1 * mm,
    )
    return title_style, sub_style, section_style, note_style

# ─────────────────────────────────────────────
# 集計テーブル生成
# ─────────────────────────────────────────────
def _make_table(items, base):
    col_widths = [CONTENT_W * 0.55, CONTENT_W * 0.20, CONTENT_W * 0.25]
    header_style = ParagraphStyle(
        "TH", fontName=RL_FONT, fontSize=9, leading=13,
        alignment=1, textColor=colors.white,
    )
    cell_l = ParagraphStyle("TD_L", fontName=RL_FONT, fontSize=9, leading=13)
    cell_r = ParagraphStyle("TD_R", fontName=RL_FONT, fontSize=9, leading=13, alignment=2)

    data = [[
        Paragraph("項目", header_style),
        Paragraph("人数", header_style),
        Paragraph("割合（％）", header_style),
    ]]
    for label, count in items:
        pct = count / base * 100 if base > 0 else 0
        data.append([
            Paragraph(label, cell_l),
            Paragraph(str(count), cell_r),
            Paragraph(f"{pct:.1f}%", cell_r),
        ])

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3c5e")),
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
# グラフ生成
# ─────────────────────────────────────────────
def _wrap(text, n=6):
    lines = textwrap.wrap(text, width=n, break_long_words=True)
    return "\n".join(lines) if lines else text

def _bar_chart(items, base):
    """縦棒グラフ → BytesIO"""
    fp = fm.FontProperties(fname=FONT_PATH)
    labels = [_wrap(l) for l, _ in items]
    counts = [c for _, c in items]
    pcts   = [c / base * 100 if base > 0 else 0 for c in counts]
    n = len(items)
    fig, ax = plt.subplots(figsize=(max(10, n * 1.4), 5.5))
    fig.patch.set_facecolor("white")
    bars = ax.bar(range(n), counts, color=BAR_COLOR, width=0.55, zorder=2)
    for bar, cnt, pct in zip(bars, counts, pcts):
        if cnt == 0:
            continue
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(counts, default=1) * 0.01,
                f"{cnt}人\n({pct:.1f}%)",
                ha="center", va="bottom", fontsize=8, fontproperties=fp)
    ax.set_xticks(list(range(n)))
    ax.set_xticklabels(labels, fontproperties=fp, fontsize=9)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(fp)
    ax.set_ylabel("人数（人）", fontproperties=fp, fontsize=9)
    ax.yaxis.grid(True, linestyle="--", alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if max(counts, default=0) > 0:
        ax.set_ylim(0, max(counts) * 1.25)
    plt.tight_layout(pad=0.5)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

def _pie_chart(items, base):
    """円グラフ → BytesIO（0件除外）"""
    fp = fm.FontProperties(fname=FONT_PATH)
    filtered = [(l, c) for l, c in items if c > 0]
    if not filtered:
        return None
    labels_raw = [l for l, _ in filtered]
    counts = [c for _, c in filtered]
    pcts   = [c / base * 100 if base > 0 else 0 for c in counts]
    pie_cols = PIE_COLORS[:len(filtered)]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    fig.patch.set_facecolor("white")
    wedges, _ = ax.pie(
        counts, labels=None, colors=pie_cols,
        startangle=90, counterclock=False,
        wedgeprops={"linewidth": 0.8, "edgecolor": "white"},
    )
    legend_labels = [f"{l}  {c}人  ({p:.1f}%)"
                     for l, c, p in zip(labels_raw, counts, pcts)]
    ax.legend(wedges, legend_labels, loc="center left",
              bbox_to_anchor=(1.0, 0.5), fontsize=8, prop=fp, frameon=False)
    ax.set_aspect("equal")
    plt.tight_layout(pad=0.5)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

def _hbar_chart(items, base):
    """横棒グラフ → BytesIO"""
    fp = fm.FontProperties(fname=FONT_PATH)
    labels = [l for l, _ in items]
    counts = [c for _, c in items]
    pcts   = [c / base * 100 if base > 0 else 0 for c in counts]
    n = len(items)
    fig, ax = plt.subplots(figsize=(9, max(3, n * 0.55 + 1)))
    fig.patch.set_facecolor("white")
    bars = ax.barh(range(n), counts, color=BAR_COLOR, height=0.55, zorder=2)
    for bar, cnt, pct in zip(bars, counts, pcts):
        if cnt == 0:
            continue
        ax.text(bar.get_width() + max(counts, default=1) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{cnt}人 ({pct:.1f}%)",
                ha="left", va="center", fontsize=8, fontproperties=fp)
    ax.set_yticks(list(range(n)))
    ax.set_yticklabels(labels, fontproperties=fp, fontsize=9)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(fp)
    ax.set_xlabel("人数（人）", fontproperties=fp, fontsize=9)
    ax.xaxis.grid(True, linestyle="--", alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if max(counts, default=0) > 0:
        ax.set_xlim(0, max(counts) * 1.3)
    ax.invert_yaxis()
    plt.tight_layout(pad=0.5)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

# ─────────────────────────────────────────────
# ブロック生成
# ─────────────────────────────────────────────
GRAPH_FUNCS = {
    "縦棒グラフ": _bar_chart,
    "円グラフ":   _pie_chart,
    "横棒グラフ": _hbar_chart,
}
GRAPH_HEIGHTS = {
    "縦棒グラフ": 0.45,
    "円グラフ":   0.42,
    "横棒グラフ": None,   # 動的
}

def _make_block(section, section_style, note_style, graph_type, base):
    items = section["items"]
    heading = Paragraph(section["title"], section_style)
    inner = []
    if section.get("note"):
        inner.append(Paragraph(section["note"], note_style))
    inner.append(_make_table(items, base))
    inner.append(Spacer(1, 3 * mm))

    fn = GRAPH_FUNCS.get(graph_type, _bar_chart)
    buf = fn(items, base)
    if buf:
        if graph_type == "横棒グラフ":
            n = len([c for _, c in items if c > 0])
            h_ratio = max(0.25, n * 0.07 + 0.1)
            img = RLImage(buf, width=CONTENT_W, height=CONTENT_W * h_ratio)
        else:
            ratio = GRAPH_HEIGHTS.get(graph_type, 0.45)
            img = RLImage(buf, width=CONTENT_W, height=CONTENT_W * ratio)
        inner.append(img)

    return KeepTogether([heading] + inner)

# ─────────────────────────────────────────────
# 公開関数
# ─────────────────────────────────────────────
def generate_pdf(
    sections: list,
    base: int,
    report_title: str,
    graph_type: str = "縦棒グラフ",
) -> bytes:
    """
    sections: [{"title": str, "note": str, "items": [(label, count), ...]}, ...]
    base:     集計ベース人数
    graph_type: "縦棒グラフ" | "円グラフ" | "横棒グラフ"
    戻り値: PDF bytes
    """
    buf_out = io.BytesIO()
    doc = SimpleDocTemplate(
        buf_out, pagesize=A4,
        leftMargin=MARGIN_LR, rightMargin=MARGIN_LR,
        topMargin=MARGIN_TB, bottomMargin=MARGIN_TB,
    )
    title_style, sub_style, section_style, note_style = _make_styles()

    story = [
        Spacer(1, 10 * mm),
        Paragraph(report_title, title_style),
        Paragraph(f"集計ベース：{base}人", sub_style),
        Spacer(1, 4 * mm),
    ]
    for sec in sections:
        story.append(_make_block(sec, section_style, note_style, graph_type, base))
        story.append(Spacer(1, 6 * mm))

    doc.build(story)
    return buf_out.getvalue()
