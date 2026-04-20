# -*- coding: utf-8 -*-
"""
OCR読み取りモジュール（Apple Vision フレームワーク + ollama LLM版）

【処理フロー】
  1. Apple Vision OCR で画像 → テキスト行リストに変換
  2. ollama（ローカルLLM）がテキストを解析して設問構造を抽出
  3. ollama 未起動 / 未インストールの場合は正規表現パーサーにフォールバック

【依存】
  - pyobjc-framework-Vision pyobjc-framework-Quartz  ← OCR
  - ollama（Pythonパッケージ）                        ← LLM解析
  - ollama アプリ（デーモン）が起動していること        ← https://ollama.com
    推奨モデル: llama3.2 / gemma3 / qwen2.5
"""

import re
import os
import json
import tempfile
from dataclasses import dataclass, field

# ─────────────────────────────────────────────
# Vision フレームワーク可用性チェック
# ─────────────────────────────────────────────
try:
    import Vision
    import Quartz
    from PIL import Image
    _VISION_OK = True
except ImportError:
    _VISION_OK = False

# ─────────────────────────────────────────────
# ollama 可用性チェック
# ─────────────────────────────────────────────
try:
    import ollama as _ollama_lib
    _OLLAMA_LIB_OK = True
except ImportError:
    _OLLAMA_LIB_OK = False

def is_ocr_available() -> bool:
    return _VISION_OK

def is_ollama_available() -> bool:
    """ollamaデーモンが起動していて、1つ以上のモデルが存在するか確認"""
    if not _OLLAMA_LIB_OK:
        return False
    try:
        models = _ollama_lib.list()
        return len(models.get("models", [])) > 0
    except Exception:
        return False

def get_ollama_models() -> list:
    """利用可能なollamaモデル名リストを返す"""
    if not _OLLAMA_LIB_OK:
        return []
    try:
        models = _ollama_lib.list()
        return [m["model"] for m in models.get("models", [])]
    except Exception:
        return []

# ─────────────────────────────────────────────
# データ構造
# ─────────────────────────────────────────────
@dataclass
class QuestionStructure:
    """1設問分の構造"""
    title: str = ""
    note: str = ""
    choices: list = field(default_factory=list)   # [str, ...]
    # 複数画像処理時の元画像情報（任意）
    source_img: int = field(default=0, repr=False, compare=False)
    source_name: str = field(default="", repr=False, compare=False)


# ─────────────────────────────────────────────
# Apple Vision OCR
# ─────────────────────────────────────────────
def _vision_ocr(pil_image) -> list:
    """
    PIL Image → 認識テキスト行リスト（Y座標上→下順）
    """
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp_path = f.name
    try:
        pil_image.save(tmp_path)

        url = Quartz.NSURL.fileURLWithPath_(tmp_path)
        req = Vision.VNRecognizeTextRequest.alloc().init()
        req.setRecognitionLanguages_(["ja-JP", "en-US"])
        req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        req.setUsesLanguageCorrection_(False)

        handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, None)
        success, err = handler.performRequests_error_([req], None)
        if not success:
            raise RuntimeError(f"Vision OCR 失敗: {err}")

        results = req.results() or []
        sorted_obs = sorted(results, key=lambda o: -o.boundingBox().origin.y)
        lines = [obs.topCandidates_(1)[0].string() for obs in sorted_obs]
        return [l for l in lines if l and l.strip()]
    finally:
        os.unlink(tmp_path)


# ─────────────────────────────────────────────
# LLMパーサー（ollama）
# ─────────────────────────────────────────────

_LLM_PROMPT_TEMPLATE = """\
以下はアンケート用紙をOCRでテキスト化した内容です。
この中から「設問」「選択肢」「補足メモ」を抽出して、JSON形式で返してください。

【重要なルール】
- 「ありがとうございました」「ご協力」「お答えください」などの定型文は無視する
- 設問タイトルは「問N」「【問N】」「Q.N」「◎」「設問N」「①②…」などで始まる行
- 選択肢は番号（1. 1） (1) ①など）付きの行、または短い選択肢の羅列
- 補足メモは「※」「（注）」「注：」などで始まる行
- 数値や割合（「120人」「45%」など）は選択肢ラベルから除去する
- 1枚の画像に複数の設問が含まれる場合はすべて抽出する

【出力形式】（JSON配列のみ。説明文は不要）
[
  {{
    "title": "設問タイトル",
    "note": "補足メモ（なければ空文字）",
    "choices": ["選択肢1", "選択肢2", ...]
  }},
  ...
]

【OCRテキスト】
{ocr_text}
"""

def _parse_with_llm(raw_lines: list, model: str = None) -> list:
    """
    ollama LLM を使って raw_lines → [QuestionStructure, ...]
    失敗した場合は None を返す（呼び出し元でフォールバック）
    """
    if not _OLLAMA_LIB_OK:
        return None

    # モデル選択（指定なしの場合は利用可能な最初のモデルを使う）
    if not model:
        models = get_ollama_models()
        if not models:
            return None
        # 日本語対応モデルを優先
        preferred = ["qwen2.5", "qwen2.5:3b", "qwen2.5:7b",
                     "gemma3", "gemma3:4b", "gemma3:12b",
                     "llama3.2", "llama3.2:3b", "llama3.1",
                     "llama3", "mistral", "phi3"]
        model = models[0]  # デフォルト
        for pref in preferred:
            for m in models:
                if m.startswith(pref):
                    model = m
                    break
            else:
                continue
            break

    ocr_text = "\n".join(raw_lines)
    prompt = _LLM_PROMPT_TEMPLATE.format(ocr_text=ocr_text)

    try:
        response = _ollama_lib.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
        )
        content = response["message"]["content"].strip()

        # JSON部分を抽出（```json ... ``` ブロックに対応）
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if json_match:
            content = json_match.group(1)
        else:
            # 配列の開始位置を探す
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end != -1:
                content = content[start:end+1]

        data = json.loads(content)
        questions = []
        for item in data:
            qs = QuestionStructure()
            qs.title = str(item.get("title", "")).strip()
            qs.note = str(item.get("note", "")).strip()
            raw_choices = item.get("choices", [])
            qs.choices = [str(c).strip() for c in raw_choices if str(c).strip()]
            if qs.title or qs.choices:
                questions.append(qs)
        return questions if questions else None

    except Exception as e:
        print(f"[LLM parse error] {e}")
        return None


# ─────────────────────────────────────────────
# 正規表現フォールバックパーサー
# ─────────────────────────────────────────────
_TITLE_PATTERNS = [
    re.compile(r"^【.+?】"),
    re.compile(r"^〔.+?〕"),
    re.compile(r"^問\s*\d+"),
    re.compile(r"^Q\s*\d+[\s.．。]", re.IGNORECASE),
    re.compile(r"^◎"),
    re.compile(r"^[①-⑳]"),
    re.compile(r"^設問\s*\d+"),
]

_NOTE_PATTERNS = [
    re.compile(r"^※"),
    re.compile(r"^\(注\)"),
    re.compile(r"^（注）"),
    re.compile(r"^注[）\)：:]"),
    re.compile(r"^\(備考\)"),
    re.compile(r"^（備考）"),
]

_SKIP_PATTERNS = [
    re.compile(r"^\s*$"),
    re.compile(r"^[\d\s.%（()\[\]、,，]+$"),
    re.compile(r"^[-―─=＝]{2,}$"),
    re.compile(r"^(項目|選択肢|回答数|人数|割合|合計|n\s*=|N\s*=)", re.IGNORECASE),
]

_IRRELEVANT_PATTERNS = [
    re.compile(r"ありがとう"),
    re.compile(r"ご協力"),
    re.compile(r"アンケート[にをはが]"),
    re.compile(r"お答えください"),
    re.compile(r"^以上$"),
    re.compile(r"^記入上の注意"),
    re.compile(r"^この調査"),
    re.compile(r"^本アンケート"),
]

def _is_title(text): return any(p.search(text) for p in _TITLE_PATTERNS)
def _is_note(text):  return any(p.search(text) for p in _NOTE_PATTERNS)
def _is_skip(text):  return any(p.search(text) for p in _SKIP_PATTERNS)
def _is_irrelevant(text): return any(p.search(text) for p in _IRRELEVANT_PATTERNS)

def _clean_choice(text: str) -> str:
    cleaned = re.sub(r"^[（(]?\s*[０-９0-9]+\s*[.．）)]\s*", "", text).strip()
    cleaned = re.sub(r"^[・□■●○◆◇▶▷→\-―─➡☑✓✔\s　]+", "", cleaned).strip()
    cleaned = re.sub(r"[\s　]+\d[\d\s.,()（）%％]*$", "", cleaned).strip()
    return cleaned if cleaned else text.strip()

def _parse_with_regex(raw_lines: list) -> list:
    """正規表現ベースのフォールバックパーサー"""
    blocks = []
    current = None
    title_seen = False

    for line in raw_lines:
        if _is_irrelevant(line):
            continue
        if _is_title(line):
            title_seen = True
            if current is not None:
                blocks.append(current)
            current = {"title_line": line, "body_lines": []}
        else:
            if not title_seen:
                continue
            current["body_lines"].append(line)

    if current is not None:
        blocks.append(current)

    questions = []
    for block in blocks:
        qs = QuestionStructure()
        qs.title = block["title_line"]
        for line in block["body_lines"]:
            if _is_skip(line) or _is_irrelevant(line):
                continue
            if _is_note(line):
                note_text = re.sub(r"^[※\s　]+", "", line).strip()
                qs.note = (qs.note + "　" + note_text).strip() if qs.note else note_text
            else:
                label = _clean_choice(line)
                if label and label not in qs.choices:
                    qs.choices.append(label)
        if qs.title or qs.choices:
            questions.append(qs)

    return questions


# ─────────────────────────────────────────────
# 公開関数
# ─────────────────────────────────────────────
def image_to_question_structure(pil_image, llm_model: str = None) -> tuple:
    """
    画像 → (QuestionStructure, raw_lines)
    後方互換用。最初の設問のみ返す。
    """
    questions, raw_lines = image_to_all_questions(pil_image, llm_model=llm_model)
    if questions:
        return questions[0], raw_lines
    return QuestionStructure(), raw_lines


def image_to_all_questions(pil_image, llm_model: str = None) -> tuple:
    """
    画像 → ([QuestionStructure, ...], raw_lines, used_llm: bool)

    1. Apple Vision OCR で生テキストを取得
    2. ollama が使えれば LLM で解析（高精度）
    3. 使えなければ正規表現フォールバック
    """
    if not _VISION_OK:
        raise RuntimeError(
            "Apple Vision OCR が利用できません。\n"
            "pip install pyobjc-framework-Vision pyobjc-framework-Quartz"
        )

    raw_lines = _vision_ocr(pil_image)

    # LLM解析を試みる
    questions = None
    used_llm = False
    if is_ollama_available():
        questions = _parse_with_llm(raw_lines, model=llm_model)
        if questions is not None:
            used_llm = True

    # フォールバック
    if questions is None:
        questions = _parse_with_regex(raw_lines)

    return questions, raw_lines, used_llm
