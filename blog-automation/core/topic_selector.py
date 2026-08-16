"""
주제 선정 엔진.

1) 키워드 조사 결과(네이버 검색량)를 받아
2) Claude가 니치별 '수익화에 좋은 주제 후보 5개'를 생성하고
3) 검색량·경쟁도·수익성 지표로 상위 3개를 확정한다.

네이버 자격증명이 없으면 Claude 단독으로 후보를 만들 수 있도록 폴백 제공.
"""
from __future__ import annotations
import json
import datetime
from dataclasses import dataclass, asdict
from typing import Optional

from core import llm

try:
    from core.keyword_research import research_niche, NICHE_SEEDS
except Exception:
    research_niche, NICHE_SEEDS = None, {}


@dataclass
class TopicCandidate:
    niche: str
    title: str            # 글 제목(롱테일 키워드 포함)
    primary_keyword: str  # 핵심 타깃 키워드
    rationale: str        # 선정 근거
    monetization: str     # adsense | coupang | both
    est_score: float = 0.0


SELECT_SYSTEM = """당신은 한국어 수익형 블로그 전략가입니다.
구글 애드센스와 쿠팡 파트너스 수익을 극대화하는 SEO 관점으로 사고합니다.
신규 워드프레스 블로그는 구글 샌드박스로 초기 경쟁이 약한 롱테일 키워드가 유리하다는 점을 압니다.
YMYL(금융/건강) 주제는 신뢰도(E-E-A-T)가 중요함을 반영합니다."""


def generate_candidates(niche: str, keyword_data: Optional[list] = None,
                        n: int = 5) -> list[TopicCandidate]:
    """니치별 주제 후보 n개 생성."""
    kw_block = ""
    if keyword_data:
        top = keyword_data[:15]
        kw_block = "실제 네이버 검색량 데이터(참고):\n" + "\n".join(
            f"- {r['keyword']} (검색량 {r['total_search']:,}, 경쟁 {r['competition']}, 점수 {r['score']})"
            for r in top
        )
    else:
        kw_block = "(네이버 검색량 데이터 없음 — 일반적 수요 지식으로 추정하세요.)"

    monet_hint = {
        "정부지원금": "주 수익은 애드센스. 정보성 롱테일로 트래픽 극대화.",
        "보험금융": "애드센스 최고 CPC 니치. 비교/조건/신청방법 롱테일 공략.",
        "건강영양": "애드센스 + 쿠팡파트너스 이중 수익. 제품 추천 연계.",
        "생활리뷰": "쿠팡파트너스 구매전환 중심. 최저가/비교/추천.",
    }.get(niche, "애드센스 중심.")

    prompt = f"""니치: '{niche}'
{monet_hint}

{kw_block}

이 니치에서 **수익화에 가장 유리한 블로그 글 주제 {n}개**를 골라주세요.
조건:
- 신규 블로그도 3~6개월 내 상위 노출 가능한 롱테일 키워드
- 검색 의도가 명확하고 광고 클릭/구매 전환이 잘 되는 주제
- 계절성/이슈성 트래픽이 있으면 가점

각 주제를 아래 JSON 배열로 출력:
[
  {{
    "title": "글 제목 (숫자/연도/구체성 포함, 클릭 유도)",
    "primary_keyword": "핵심 타깃 키워드",
    "rationale": "왜 수익성이 좋은지 1문장",
    "monetization": "adsense | coupang | both",
    "est_score": 0~100 수익성 추정점수(숫자)
  }}
]

오늘 날짜는 {datetime.date.today()} 입니다. 제목에 연도를 넣을 경우 반드시 이 날짜 기준의 연도를 사용하세요."""

    data = llm.ask_json(prompt, system=SELECT_SYSTEM)
    if isinstance(data, dict):
        data = data.get("topics") or data.get("candidates") or [data]
    out = []
    for d in data[:n]:
        out.append(
            TopicCandidate(
                niche=niche,
                title=d.get("title", ""),
                primary_keyword=d.get("primary_keyword", ""),
                rationale=d.get("rationale", ""),
                monetization=d.get("monetization", "adsense"),
                est_score=float(d.get("est_score", 0) or 0),
            )
        )
    return out


def select_top_niches(all_niches: list[str], pick: int = 3,
                      use_naver: bool = True) -> dict:
    """
    여러 니치를 조사해서 후보를 만들고, 니치 대표점수로 상위 `pick`개 니치를 확정.
    반환: {"chosen_niches": [...], "candidates": {niche: [TopicCandidate,...]}}
    """
    candidates: dict[str, list[TopicCandidate]] = {}
    niche_score: dict[str, float] = {}

    for niche in all_niches:
        kw = None
        if use_naver and research_niche:
            try:
                kw = research_niche(niche, top_n=20)
            except Exception as e:
                print(f"[i] {niche} 네이버 조사 생략({e}) → Claude 추정 사용")
        cands = generate_candidates(niche, keyword_data=kw)
        candidates[niche] = cands
        # 니치 점수 = 상위 후보 평균
        if cands:
            niche_score[niche] = sum(c.est_score for c in cands[:3]) / min(3, len(cands))
        else:
            niche_score[niche] = 0.0

    chosen = sorted(niche_score, key=niche_score.get, reverse=True)[:pick]
    return {
        "chosen_niches": chosen,
        "niche_scores": niche_score,
        "candidates": {n: [asdict(c) for c in candidates[n]] for n in candidates},
    }


if __name__ == "__main__":
    niches = list(NICHE_SEEDS.keys()) or ["정부지원금", "보험금융", "건강영양", "생활리뷰"]
    result = select_top_niches(niches, pick=3)
    print("\n===== 확정 니치 TOP 3 =====")
    for n in result["chosen_niches"]:
        print(f"\n▶ {n} (점수 {result['niche_scores'][n]:.1f})")
        for c in result["candidates"][n][:5]:
            print(f"   - {c['title']}  [{c['monetization']}]  ({c['est_score']})")
