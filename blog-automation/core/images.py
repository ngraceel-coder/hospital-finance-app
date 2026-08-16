"""
이미지 자동화.

1) generate_thumbnail(): 제목이 박힌 카드형 대표이미지(1200x630) 생성.
   - Pillow + 나눔고딕 폰트(서버: sudo apt-get install -y fonts-nanum)
   - 니치별 색상 그라데이션 → 블로그에 브랜드 통일감
   - 비용 0원, 저작권 문제 0

2) fetch_stock_photo(): Pexels 무료 API로 본문용 스톡사진 다운로드.
   - .env 에 PEXELS_API_KEY 가 있을 때만 동작 (없으면 조용히 생략)
   - https://www.pexels.com/api/ 에서 무료 키 발급
"""
from __future__ import annotations
import os
import io
import textwrap
from pathlib import Path

from config import config

# 니치별 그라데이션 (위 색 → 아래 색) + 배지 텍스트
NICHE_STYLES = {
    "정부지원금": (("#0f4c81", "#2e86de"), "지원금 정보"),
    "보험금융": (("#134e4a", "#14b8a6"), "금융 꿀팁"),
    "건강영양": (("#7c2d12", "#f97316"), "건강 정보"),
    "생활리뷰": (("#4c1d95", "#8b5cf6"), "리뷰 · 추천"),
}
DEFAULT_STYLE = (("#1f2937", "#4b5563"), "생활 정보")

# 한글 폰트 후보 (위에서부터 시도)
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumBarunGothicBold.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",  # 맥 로컬 테스트용
]


def _find_font() -> str | None:
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def _hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def generate_thumbnail(title: str, niche: str = "", site_name: str = "clearskysogood.net",
                       out_dir: Path | None = None, slug: str = "thumb") -> Path | None:
    """
    카드형 대표이미지 생성. 성공 시 파일 경로, 한글 폰트가 없으면 None(경고 출력).
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("   [i] Pillow 미설치 → 썸네일 생략 (pip install Pillow)")
        return None

    font_path = _find_font()
    if not font_path:
        print("   [i] 한글 폰트 없음 → 썸네일 생략 (sudo apt-get install -y fonts-nanum)")
        return None

    W, H = 1200, 630
    (top_hex, bottom_hex), badge = NICHE_STYLES.get(niche, DEFAULT_STYLE)
    top, bottom = _hex_to_rgb(top_hex), _hex_to_rgb(bottom_hex)

    # 세로 그라데이션
    img = Image.new("RGB", (W, H))
    for y in range(H):
        t = y / H
        row = tuple(int(top[c] + (bottom[c] - top[c]) * t) for c in range(3))
        for_draw = Image.new("RGB", (W, 1), row)
        img.paste(for_draw, (0, y))

    draw = ImageDraw.Draw(img)

    # 반투명 어두운 오버레이 박스(텍스트 가독성)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([60, 140, W - 60, H - 120], fill=(0, 0, 0, 70))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    badge_font = ImageFont.truetype(font_path, 34)
    title_font = ImageFont.truetype(font_path, 64)
    site_font = ImageFont.truetype(font_path, 28)

    # 배지
    draw.rounded_rectangle([60, 60, 60 + 30 + badge_font.getlength(badge), 118],
                           radius=12, fill=(255, 255, 255, 255))
    draw.text((75, 68), badge, font=badge_font, fill=top_hex)

    # 제목 (줄바꿈: 한 줄 최대 ~14자)
    lines = textwrap.wrap(title, width=14)[:4]
    y = 190
    for line in lines:
        draw.text((90, y), line, font=title_font, fill="white")
        y += 86

    # 사이트명
    draw.text((90, H - 100), site_name, font=site_font, fill=(255, 255, 255))

    out_dir = out_dir or (config.output_dir / "thumbs")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug[:50]}.png"
    img.save(path, "PNG", optimize=True)
    return path


def fetch_stock_photo(query_en: str, out_dir: Path | None = None,
                      slug: str = "photo") -> Path | None:
    """
    Pexels에서 가로형 사진 1장 다운로드. 키 없으면 None.
    query_en: 영문 검색어 (슬러그 단어 재활용 추천)
    """
    api_key = getattr(config, "pexels_api_key", "") or os.getenv("PEXELS_API_KEY", "")
    if not api_key or not query_en:
        return None
    import requests

    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query_en, "per_page": 3, "orientation": "landscape"},
            headers={"Authorization": api_key},
            timeout=15,
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if not photos:
            return None
        url = photos[0]["src"]["large"]  # 940px 안팎, 본문용으로 적당
        img = requests.get(url, timeout=20)
        img.raise_for_status()
        out_dir = out_dir or (config.output_dir / "photos")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{slug[:50]}.jpg"
        path.write_bytes(img.content)
        return path
    except Exception as e:
        print(f"   [i] 스톡사진 생략({e})")
        return None


if __name__ == "__main__":
    p = generate_thumbnail(
        "2026년 근로장려금 대상 조건 총정리",
        niche="정부지원금",
        slug="test-thumb",
    )
    print("썸네일:", p)
