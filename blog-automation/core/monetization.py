"""
수익화 삽입 엔진.

콘텐츠 생성 단계에서 남긴 플레이스홀더를 실제 수익 코드로 치환한다.
  [[AD]]       → 구글 애드센스 광고 유닛
  [[COUPANG]]  → 쿠팡 파트너스 제휴 링크/배너

애드센스/쿠팡 자격증명이 없으면 해당 플레이스홀더를 제거(빈칸)한다.
"""
from __future__ import annotations
import re

from config import config


def adsense_unit() -> str:
    """반응형 애드센스 인아티클 광고 유닛 HTML."""
    if not (config.adsense_client_id and config.adsense_slot_id):
        return ""
    return f"""
<div class="ad-container" style="margin:24px 0;text-align:center;">
  <ins class="adsbygoogle"
       style="display:block; text-align:center;"
       data-ad-layout="in-article"
       data-ad-format="fluid"
       data-ad-client="{config.adsense_client_id}"
       data-ad-slot="{config.adsense_slot_id}"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
</div>""".strip()


def adsense_header_script() -> str:
    """<head>에 한 번 들어갈 애드센스 로더 (테마에 넣거나 글 상단에 1회)."""
    if not config.adsense_client_id:
        return ""
    return (
        '<script async '
        f'src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={config.adsense_client_id}" '
        'crossorigin="anonymous"></script>'
    )


def coupang_block(keyword: str = "") -> str:
    """
    쿠팡 파트너스 제휴 블록.
    실제 상품 링크는 파트너스에서 생성한 딥링크를 넣어야 하므로,
    여기서는 검색 딥링크 형태의 안내 박스를 생성한다.
    태그가 없으면 빈 문자열.
    """
    tag = config.coupang_partners_tag
    if not tag:
        return ""
    # 쿠팡 파트너스 검색 딥링크 패턴 (실제 상품 링크로 교체 권장)
    from urllib.parse import quote
    q = quote(keyword) if keyword else ""
    link = f"https://link.coupang.com/a/{tag}"
    return f"""
<div class="coupang-partners" style="border:1px solid #eee;border-radius:12px;padding:16px;margin:24px 0;background:#fafafa;">
  <p style="margin:0 0 8px;font-weight:600;">🛒 추천 상품 보러가기</p>
  <a href="{link}" target="_blank" rel="nofollow sponsored noopener"
     style="display:inline-block;padding:10px 18px;background:#ff4757;color:#fff;border-radius:8px;text-decoration:none;">
     쿠팡에서 '{keyword or "관련 상품"}' 최저가 확인 →</a>
  <p style="margin:8px 0 0;font-size:12px;color:#999;">
    이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.
  </p>
</div>""".strip()


def inject(html: str, monetization: str = "adsense", keyword: str = "") -> str:
    """플레이스홀더를 실제 수익 코드로 치환."""
    ad = adsense_unit()
    coupang = coupang_block(keyword) if monetization in ("coupang", "both") else ""

    # [[AD]] 치환 (없으면 자동 삽입은 안 함 — 콘텐츠 단계에서 위치 지정)
    html = html.replace("[[AD]]", ad)
    # [[COUPANG]] 치환
    html = html.replace("[[COUPANG]]", coupang)

    # 혹시 남은 플레이스홀더 정리
    html = re.sub(r"\[\[(AD|COUPANG)\]\]", "", html)
    return html


def ensure_ads_present(html: str, monetization: str = "adsense", keyword: str = "") -> str:
    """
    플레이스홀더가 하나도 없던 경우를 대비해,
    문단 사이에 광고를 자동 배치하는 폴백.
    """
    if "adsbygoogle" in html or not config.adsense_client_id:
        return html
    parts = re.split(r"(</h2>)", html)
    if len(parts) < 3:
        return html + "\n" + adsense_unit()
    # 두 번째 h2 뒤에 광고 하나 삽입
    inserted = "".join(parts[:3]) + "\n" + adsense_unit() + "\n" + "".join(parts[3:])
    return inserted


if __name__ == "__main__":
    sample = "<h2>소개</h2><p>본문</p>[[AD]]<p>추천</p>[[COUPANG]]"
    print(inject(sample, monetization="both", keyword="유산균"))
