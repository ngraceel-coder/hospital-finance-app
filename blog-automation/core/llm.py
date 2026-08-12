"""
Claude API 공용 래퍼.
콘텐츠 생성/주제 선정에서 공통으로 사용한다.
"""
from __future__ import annotations
import json
from typing import Optional

from config import config


def _client():
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError(
            "anthropic 패키지가 없습니다. pip install anthropic 를 실행하세요."
        ) from e
    if not config.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY 가 설정되지 않았습니다 (.env).")
    return anthropic.Anthropic(api_key=config.anthropic_api_key)


def ask(prompt: str, system: str = "", max_tokens: int = 4096,
        temperature: float = 0.7) -> str:
    """Claude에게 프롬프트를 보내고 텍스트 응답을 반환."""
    client = _client()
    kwargs = dict(
        model=config.claude_model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    return "".join(block.text for block in resp.content if block.type == "text")


def ask_json(prompt: str, system: str = "", max_tokens: int = 4096) -> dict | list:
    """
    JSON 응답을 강제하고 파싱해서 반환.
    Claude가 코드블록으로 감싸는 경우도 처리.
    """
    system = (system + "\n\n반드시 유효한 JSON만 출력하세요. 설명 문장 금지.").strip()
    raw = ask(prompt, system=system, max_tokens=max_tokens, temperature=0.4)
    raw = raw.strip()
    # ```json ... ``` 제거
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    # 첫 { 또는 [ 부터 마지막 } 또는 ] 까지 추출 (안전장치)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = min(
            (raw.find(c) for c in "{[" if raw.find(c) != -1), default=-1
        )
        end = max(raw.rfind("}"), raw.rfind("]"))
        if start != -1 and end != -1:
            return json.loads(raw[start : end + 1])
        raise
