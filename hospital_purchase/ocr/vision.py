"""Claude Vision API 로 명세서 이미지 → 구조화 JSON (계획서 6.3).

anthropic SDK / API 키가 없으면 예외를 던진다(호출부에서 수동 입력으로 유도).
"""
import base64
import json
import mimetypes

from config import ANTHROPIC_API_KEY, VISION_MODEL
from ocr.prompts import build_prompt


def vision_available() -> bool:
    if not ANTHROPIC_API_KEY:
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except Exception:
        return False


def _encode(image_path):
    mime = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return mime, data


def _extract_json(text: str) -> dict:
    """모델 응답에서 JSON 부분만 안전하게 파싱."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("OCR 응답에서 JSON 을 찾지 못했습니다.")
    return json.loads(text[start:end + 1])


def run_ocr(image_path: str, vendor: dict = None) -> dict:
    """이미지 → 파싱 결과 dict. 실패 시 예외."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY 가 설정되지 않았습니다(.env 확인).")
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    mime, data = _encode(image_path)
    prompt = build_prompt(vendor)

    resp = client.messages.create(
        model=VISION_MODEL,
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": mime, "data": data}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    parsed = _extract_json(text)
    parsed["_raw"] = text
    return parsed
