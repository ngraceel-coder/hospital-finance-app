"""
콘텐츠 생성 엔진 - Claude API로 SEO 최적화 아티클 생성.

출력: 제목, 본문(HTML), 메타디스크립션, 태그, 슬러그, 카테고리
품질 게이트(글자수/제목/구조)를 통과해야 발행 단계로 넘어간다.
"""
from __future__ import annotations
import re
import datetime
from dataclasses import dataclass, field, asdict

from core import llm

try:
    from slugify import slugify
except ImportError:
    def slugify(text, **kw):
        return re.sub(r"[^a-z0-9가-힣]+", "-", text.lower()).strip("-")


CONTENT_SYSTEM = """당신은 한국어 수익형 블로그 전문 작가입니다.
- 구글 검색 상위 노출(SEO)과 애드센스 수익을 동시에 노립니다.
- 독자에게 실질적 정보를 주면서 자연스럽게 광고/제휴가 어울리는 글을 씁니다.
- 서론-본론(소제목 여러 개)-결론(FAQ 포함) 구조를 지킵니다.
- 핵심 키워드를 제목·첫 문단·소제목·마무리에 자연스럽게 배치합니다.
- 과장/허위 정보를 쓰지 않고, 금융/건강 주제는 '참고용이며 전문가 상담 권장' 면책을 넣습니다.
- 출력은 순수 HTML 본문(<h2>,<h3>,<p>,<ul>,<table> 등)만. <html><body> 태그는 넣지 않습니다."""


@dataclass
class Article:
    title: str
    html: str
    meta_description: str
    tags: list = field(default_factory=list)
    category: str = ""
    slug: str = ""
    primary_keyword: str = ""
    niche: str = ""
    word_count: int = 0
    monetization: str = "adsense"

    def to_dict(self):
        return asdict(self)


def _plain_len(html: str) -> int:
    return len(re.sub(r"<[^>]+>", "", html))


def generate_article(title: str, primary_keyword: str, niche: str = "",
                     monetization: str = "adsense", min_chars: int = 1500) -> Article:
    """단일 아티클 생성."""
    today = datetime.date.today()
    prompt = f"""아래 조건으로 블로그 글을 작성하세요.
오늘 날짜는 {today} 입니다. 제목/본문에 연도를 쓸 때는 반드시 이 날짜 기준의 연도를 사용하고, 지난 연도 정보는 최신 기준으로 서술하세요.

제목(참고): {title}
핵심 키워드: {primary_keyword}
니치: {niche}
수익화: {monetization}

요구사항:
1. 제목은 클릭을 유도하되 핵심 키워드를 포함 (필요시 다듬어도 됨)
2. 본문은 최소 {min_chars}자 이상, <h2>/<h3> 소제목으로 구조화
3. 표(<table>)나 목록(<ul>)을 1개 이상 활용해 가독성↑
4. 마지막에 <h2>자주 묻는 질문(FAQ)</h2> 3개 포함
5. 금융/건강 주제면 맨 아래 면책 문구 <p><em>...</em></p> 추가
6. 쿠팡 연계면 제품 추천 자리에 [[COUPANG]] 플레이스홀더를 1~2곳 넣기
7. 광고 삽입 위치에 [[AD]] 플레이스홀더를 본문 상/중/하 3곳에 넣기

아래 JSON으로만 출력:
{{
  "title": "최종 제목",
  "meta_description": "검색결과용 요약 (120자 내외, 키워드 포함)",
  "tags": ["태그1","태그2","태그3","태그4","태그5"],
  "category": "카테고리명",
  "html": "본문 HTML (플레이스홀더 포함)"
}}"""

    data = llm.ask_json(prompt, system=CONTENT_SYSTEM, max_tokens=16000)
    html = data.get("html", "")
    art = Article(
        title=data.get("title", title),
        html=html,
        meta_description=data.get("meta_description", ""),
        tags=data.get("tags", []),
        category=data.get("category", niche),
        slug=slugify(data.get("title", title), allow_unicode=False)[:80]
        or slugify(primary_keyword),
        primary_keyword=primary_keyword,
        niche=niche,
        word_count=_plain_len(html),
        monetization=monetization,
    )
    return art


def quality_gate(art: Article, min_chars: int = 1200) -> tuple[bool, list]:
    """발행 전 품질 검사. (통과여부, 문제목록)"""
    problems = []
    if art.word_count < min_chars:
        problems.append(f"본문이 짧음 ({art.word_count}자 < {min_chars})")
    if not art.title:
        problems.append("제목 없음")
    if "<h2" not in art.html.lower():
        problems.append("소제목(h2) 없음 → SEO 구조 미흡")
    if not art.meta_description:
        problems.append("메타 디스크립션 없음")
    if art.primary_keyword and art.primary_keyword not in art.title + art.html:
        problems.append("핵심 키워드가 본문에 없음")
    return (len(problems) == 0, problems)


if __name__ == "__main__":
    art = generate_article(
        title="2025 근로장려금 신청 자격과 지급일 총정리",
        primary_keyword="근로장려금 신청 자격",
        niche="정부지원금",
        monetization="adsense",
    )
    ok, probs = quality_gate(art)
    print(f"제목: {art.title}")
    print(f"글자수: {art.word_count}  통과: {ok}  {probs}")
    print(art.html[:500])
