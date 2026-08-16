"""
키워드 조사 엔진 - 네이버 검색광고 API (keywordstool)

네이버 검색광고 광고주 가입 후 발급받은 API 키로
검색량·경쟁도·예상 클릭단가를 조회하고, '수익성 점수'를 계산한다.

수익성 점수 = 검색량(트래픽 잠재력) × 경쟁도역수(진입가능성) × CPC가중(단가)

- API 문서: https://naver.github.io/searchad-apidoc/
- 광고주 가입만 하면 호출은 무료 (광고비 집행 불필요)
- 호출 제한: 초당 3회 권장 (초과 시 429)
"""
from __future__ import annotations
import time
import hmac
import hashlib
import base64
import json
from dataclasses import dataclass, asdict
from typing import Optional

import requests

from config import config

BASE_URL = "https://api.searchad.naver.com"
KEYWORDSTOOL_PATH = "/keywordstool"


def _signature(timestamp: str, method: str, path: str, secret_key: str) -> str:
    """네이버 검색광고 API HMAC-SHA256 서명 생성."""
    message = f"{timestamp}.{method}.{path}"
    digest = hmac.new(
        secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _headers(method: str, path: str) -> dict:
    timestamp = str(round(time.time() * 1000))
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": config.naver_ad_api_key,
        "X-Customer": str(config.naver_ad_customer_id),
        "X-Signature": _signature(
            timestamp, method, path, config.naver_ad_secret_key
        ),
    }


def _to_int(val) -> int:
    """네이버 API는 검색량이 적을 때 '< 10' 문자열을 반환한다."""
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        s = val.replace("<", "").replace(",", "").strip()
        try:
            return int(s)
        except ValueError:
            return 0
    return 0


# 경쟁도 문자열 → 진입가능성 가중치 (낮을수록 진입 쉬움 → 높은 점수)
_COMP_WEIGHT = {"낮음": 1.0, "중간": 0.6, "높음": 0.3}


@dataclass
class KeywordStat:
    keyword: str
    pc_search: int          # PC 월간 검색량
    mobile_search: int      # 모바일 월간 검색량
    total_search: int       # 합계
    competition: str        # 낮음/중간/높음
    avg_click_pc: float     # PC 평균 클릭수
    avg_click_mobile: float
    score: float = 0.0      # 수익성 점수

    def compute_score(self, cpc_weight: float = 1.0) -> float:
        """
        수익성 점수:
          log 스케일 검색량 × 경쟁도 진입가중 × 니치 CPC 가중
        검색량이 지나치게 큰 초고경쟁 키워드가 점수를 독식하지 않도록 log 사용.
        """
        import math
        vol = math.log10(self.total_search + 1)
        comp = _COMP_WEIGHT.get(self.competition, 0.5)
        self.score = round(vol * comp * cpc_weight * 100, 1)
        return self.score


class KeywordResearcher:
    """네이버 검색광고 API 래퍼."""

    def __init__(self):
        self.session = requests.Session()

    def fetch(self, seed_keywords: list[str], show_detail: bool = True) -> list[KeywordStat]:
        """
        시드 키워드로 연관 키워드 + 검색량 조회.
        네이버 API는 hintKeywords 로 최대 5개까지 받고 연관 키워드를 확장 반환한다.
        """
        if not config.naver_ad_api_key:
            raise RuntimeError(
                "네이버 검색광고 API 키가 없습니다. .env 의 NAVER_AD_* 를 설정하세요."
            )

        results: list[KeywordStat] = []
        # API는 hintKeywords 최대 5개 권장 → 청크로 나눠 호출
        for i in range(0, len(seed_keywords), 5):
            chunk = seed_keywords[i : i + 5]
            params = {
                "hintKeywords": ",".join(chunk),
                "showDetail": "1" if show_detail else "0",
            }
            headers = _headers("GET", KEYWORDSTOOL_PATH)
            try:
                resp = self.session.get(
                    BASE_URL + KEYWORDSTOOL_PATH,
                    params=params,
                    headers=headers,
                    timeout=15,
                )
                resp.raise_for_status()
            except requests.HTTPError as e:
                if resp.status_code == 429:
                    time.sleep(1)  # 레이트리밋 → 잠시 대기 후 스킵
                    continue
                raise RuntimeError(f"네이버 API 오류: {e}\n{resp.text}") from e

            for row in resp.json().get("keywordList", []):
                stat = KeywordStat(
                    keyword=row.get("relKeyword", ""),
                    pc_search=_to_int(row.get("monthlyPcQcCnt", 0)),
                    mobile_search=_to_int(row.get("monthlyMobileQcCnt", 0)),
                    total_search=0,
                    competition=row.get("compIdx", "중간"),
                    avg_click_pc=float(row.get("monthlyAvePcClkCnt", 0) or 0),
                    avg_click_mobile=float(row.get("monthlyAveMobileClkCnt", 0) or 0),
                )
                stat.total_search = stat.pc_search + stat.mobile_search
                results.append(stat)

            time.sleep(0.4)  # 초당 3회 제한 준수

        return results

    def score_and_rank(
        self, stats: list[KeywordStat], cpc_weight: float = 1.0, top_n: int = 30
    ) -> list[KeywordStat]:
        """수익성 점수 계산 후 상위 N개 반환."""
        for s in stats:
            s.compute_score(cpc_weight)
        ranked = sorted(stats, key=lambda x: x.score, reverse=True)
        return ranked[:top_n]


# 니치별 CPC 가중치 (금융/보험/부동산이 애드센스 단가 최상위)
NICHE_CPC_WEIGHT = {
    "정부지원금": 1.3,
    "보험금융": 2.0,
    "부동산정책": 1.8,
    "건강영양": 1.2,
    "생활리뷰": 0.9,
    "default": 1.0,
}

# 니치별 시드 키워드 (실제 조사의 출발점)
NICHE_SEEDS = {
    "정부지원금": ["정부지원금", "근로장려금", "청년지원금", "소상공인지원", "정책자금"],
    "보험금융": ["실손보험", "어린이보험", "자동차보험", "전세자금대출", "신용점수"],
    "부동산정책": ["전세보증금", "청약통장", "재산세", "종합부동산세", "주택담보대출"],
    "건강영양": ["유산균", "오메가3", "비타민D", "루테인", "단백질보충제"],
    "생활리뷰": ["로봇청소기", "공기청정기", "제습기", "가습기", "무선청소기"],
}


def research_niche(niche: str, top_n: int = 20) -> list[dict]:
    """
    니치 이름으로 키워드 조사를 실행하고 상위 키워드(dict) 반환.
    네이버 자격증명이 없으면 RuntimeError.
    """
    seeds = NICHE_SEEDS.get(niche, [niche])
    weight = NICHE_CPC_WEIGHT.get(niche, NICHE_CPC_WEIGHT["default"])
    researcher = KeywordResearcher()
    stats = researcher.fetch(seeds)
    ranked = researcher.score_and_rank(stats, cpc_weight=weight, top_n=top_n)
    return [asdict(s) for s in ranked]


if __name__ == "__main__":
    # 단독 실행 시: 4개 니치 전부 조사해서 출력
    import sys

    missing = config.validate(need=("naver",))
    if missing:
        print(f"[!] 네이버 API 설정 누락: {', '.join(missing)}")
        print("    .env 파일에 NAVER_AD_API_KEY / SECRET / CUSTOMER_ID 를 넣으세요.")
        sys.exit(1)

    for niche in NICHE_SEEDS:
        print(f"\n===== [{niche}] 수익 키워드 TOP 10 =====")
        try:
            rows = research_niche(niche, top_n=10)
            for r in rows:
                print(
                    f"  {r['score']:>6.1f}  {r['keyword']:<20} "
                    f"검색량 {r['total_search']:>7,}  경쟁 {r['competition']}"
                )
        except Exception as e:
            print(f"  오류: {e}")
