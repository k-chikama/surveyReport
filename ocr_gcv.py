# -*- coding: utf-8 -*-
import base64
import os
from io import BytesIO

import requests

from ocr_reader import _parse_with_regex, QuestionStructure  # noqa: F401


def is_gcv_available() -> bool:
    return bool(os.environ.get("GOOGLE_VISION_API_KEY"))


def _to_base64(pil_image) -> str:
    buf = BytesIO()
    pil_image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def image_to_text(pil_image, api_key: str) -> str:
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    payload = {
        "requests": [{
            "image": {"content": _to_base64(pil_image)},
            "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
            "imageContext": {"languageHints": ["ja", "en"]},
        }]
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["responses"][0]["fullTextAnnotation"]["text"]
    except (KeyError, IndexError):
        return ""


def image_to_questions(pil_image, api_key: str) -> tuple:
    """PIL Image → ([QuestionStructure, ...], raw_text)"""
    raw_text = image_to_text(pil_image, api_key)
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    questions = _parse_with_regex(lines)
    return questions, raw_text
