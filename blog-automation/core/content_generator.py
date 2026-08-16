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


CONTENT_SYSTEM = """당신은 구독자가 많은 한국어 생활정보 블로거입니다. AI가 아니라 옆집의 꼼꼼한 지인이 알려주듯 씁니다.

[도입부 — 3초 안에 붙잡기, 이 3단 구조 필수]
1) 결론/약속: 첫 문장에서 이 글이 주는 이득을 구체적 숫자와 함께 단언 (예: "이 글 5분이면 최대 330만원 받는 조건을 확인할 수 있어요.")
2) 공감: 독자의 상황·불안을 한 문장으로 찌르기 (예: "매년 신청 시기를 놓쳐서 못 받는 분이 수십만 명입니다.")
3) 미리보기: 아래에서 다룰 것 예고 한 문장
- 금지: 사전적 정의로 시작, "현대 사회에서", "오늘은 ~에 대해 알아보겠습니다" 류의 상투적 도입

[문체 — AI 냄새 제거]
- 짧은 문단(2~3문장), 문장 길이를 다양하게. 가끔 한 문장짜리 강조 단락 사용 ("이게 핵심이에요.")
- 구어체 존댓말 섞기: ~해요, ~인데요, ~거든요. 독자에게 직접 말 걸기 ("혹시 ~하고 계신가요?")
- 손실 회피 프레이밍: "모르면 못 받는", "이거 놓치면 연 ○○만원 손해"
- 금지 표현: "알아보겠습니다", "살펴보겠습니다", "결론적으로", "종합적으로", "~라고 할 수 있습니다", 모든 문단이 같은 길이인 것
- 모든 주장에 구체적 숫자·금액·날짜·기준을 붙일 것. 두루뭉술한 문장("많은 혜택이 있습니다") 금지
- 사실이 아닌 개인 경험 날조는 금지. 대신 "많은 분들이 놓치는 부분인데요", "후기들을 보면" 같은 정직한 표현 사용

[본문 구조]
- H2 소제목 3~5개. 소제목도 정보+후킹 (예: "신청 전 꼭 확인: 탈락 사유 1위")
- 반드시 포함: ① 비교표 또는 정리표(실제 수치) ② '흔한 실수/놓치기 쉬운 것' 섹션 ③ 실전 팁 1개 이상
- 마무리: 핵심 3줄 요약 + 행동 유도 한 문장 (예: "오늘 5분만 투자해서 신청 자격부터 확인해보세요.")

[불변 규칙]
- 핵심 키워드를 제목·첫 문단·소제목 1개·마무리에 자연스럽게 배치 (SEO)
- 과장/허위 금지. 금융/건강 주제는 맨 아래 '참고용, 전문가 상담 권장' 면책 필수
- 출력은 순수 HTML 본문(<h2>,<h3>,<p>,<ul>,<table> 등)만. <html><body> 태그 금지"""


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
                     monetization: str = "adsense", min_chars: int = 1500,
                     recent_posts: list = None) -> Article:
    """단일 아티클 생성. recent_posts: [{'title','link'}] — 내부링크 삽입용."""
    today = datetime.date.today()
    internal_block = ""
    if recent_posts:
        links = "\n".join(f"- {p['title']} → {p['link']}" for p in recent_posts[:8])
        internal_block = f"""
[내부링크 — SEO·체류시간 핵심]
이 블로그의 기존 글 목록입니다. 이 중 지금 글과 주제가 연관된 것이 있으면
본문 중 자연스러운 위치에 1~2개를 <a href="링크">앵커텍스트</a> 로 삽입하세요.
앵커텍스트는 "여기"가 아니라 글 내용을 설명하는 문구로. 연관 글이 없으면 삽입하지 마세요.
{links}
"""
    prompt = f"""아래 조건으로 블로그 글을 작성하세요.
오늘 날짜는 {today} 입니다. 제목/본문에 연도를 쓸 때는 반드시 이 날짜 기준의 연도를 사용하고, 지난 연도 정보는 최신 기준으로 서술하세요.
{internal_block}

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
  "slug": "short-english-slug (영문 소문자 3~6단어, 하이픈 구분, 핵심키워드 번역 포함)",
  "meta_description": "검색결과용 요약 (120자 내외, 키워드 포함)",
  "tags": ["태그1","태그2","태그3","태그4","태그5"],
  "category": "카테고리명",
  "faq": [{{"q": "질문1", "a": "답변1"}}, {{"q": "질문2", "a": "답변2"}}, {{"q": "질문3", "a": "답변3"}}],
  "html": "본문 HTML (플레이스홀더 포함)"
}}"""

    data = llm.ask_json(prompt, system=CONTENT_SYSTEM, max_tokens=16000)
    html = data.get("html", "")

    # FAQ 구조화 데이터(JSON-LD) — 구글 리치 결과(질문 펼침) 노출용
    faq = data.get("faq") or []
    if faq:
        import json as _json
        faq_schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": item.get("q", ""),
                    "acceptedAnswer": {"@type": "Answer", "text": item.get("a", "")},
                }
                for item in faq if item.get("q")
            ],
        }
        html += (
            '\n<script type="application/ld+json">'
            + _json.dumps(faq_schema, ensure_ascii=False)
            + "</script>"
        )

    # 슬러그: Claude가 지은 짧은 영문 슬러그 우선, 없으면 로마자화 폴백
    ai_slug = slugify(data.get("slug", ""), allow_unicode=False)[:60]
    art = Article(
        title=data.get("title", title),
        html=html,
        meta_description=data.get("meta_description", ""),
        tags=data.get("tags", []),
        category=data.get("category", niche),
        slug=ai_slug
        or slugify(data.get("title", title), allow_unicode=False)[:80]
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
