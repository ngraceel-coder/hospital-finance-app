"""
전체 파이프라인 오케스트레이션.

키워드 조사 → 주제 선정 → 콘텐츠 생성 → 수익화 삽입 → 워드프레스 발행
을 하나로 연결한다.

사용:
    from core.pipeline import run_full_pipeline
    run_full_pipeline()
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

from config import config
from core import topic_selector, content_generator, monetization, wordpress_publisher

NICHES = ["정부지원금", "보험금융", "부동산정책", "건강영양", "생활리뷰"]
HISTORY_FILE = config.output_dir / "published.json"


def _load_history() -> list:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return []


def _save_history(entries: list):
    config.ensure_dirs()
    HISTORY_FILE.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _already_done(title: str, history: list) -> bool:
    return any(h.get("title") == title for h in history)


def select_topics(pick_niches: int = 3, use_naver: bool = True) -> dict:
    """1~2단계: 니치 조사 + 주제 확정."""
    print("① 키워드 조사 + 주제 선정 중...")
    result = topic_selector.select_top_niches(NICHES, pick=pick_niches, use_naver=use_naver)
    print(f"   확정 니치: {result['chosen_niches']}")
    return result


def produce_one(candidate: dict, recent_posts: list = None) -> content_generator.Article:
    """3~4단계: 단일 후보 → 콘텐츠 생성 + 수익화 삽입."""
    art = content_generator.generate_article(
        title=candidate["title"],
        primary_keyword=candidate["primary_keyword"],
        niche=candidate["niche"],
        monetization=candidate.get("monetization", "adsense"),
        recent_posts=recent_posts,
    )
    ok, problems = content_generator.quality_gate(art)
    if not ok:
        print(f"   ⚠ 품질 경고: {problems}")
    # 수익화 코드 삽입
    art.html = monetization.inject(
        art.html, monetization=art.monetization, keyword=art.primary_keyword
    )
    art.html = monetization.ensure_ads_present(
        art.html, monetization=art.monetization, keyword=art.primary_keyword
    )
    return art


def run_full_pipeline(posts_per_niche: int = 1, pick_niches: int = 3,
                      use_naver: bool = True, status: str = None) -> list:
    """
    전체 실행: 확정 니치 각각에서 상위 후보로 글을 생성·발행.
    반환: 발행 결과 리스트.
    """
    config.ensure_dirs()
    history = _load_history()
    results = []

    selection = select_topics(pick_niches=pick_niches, use_naver=use_naver)

    for niche in selection["chosen_niches"]:
        candidates = selection["candidates"][niche]
        made = 0
        for cand in candidates:
            if made >= posts_per_niche:
                break
            if _already_done(cand["title"], history):
                continue
            print(f"\n② [{niche}] 콘텐츠 생성: {cand['title']}")
            try:
                # 내부링크용: 실제 발행된 최근 글 목록 (성공 블로그 벤치마킹 반영)
                recent = [
                    {"title": h["title"], "link": h["result"]["link"]}
                    for h in history[-15:]
                    if isinstance(h.get("result"), dict) and h["result"].get("link")
                ]
                art = produce_one(cand, recent_posts=recent)
                print(f"   글자수 {art.word_count} · 태그 {len(art.tags)}개")
                # 대표이미지(카드형 썸네일) 자동 생성
                thumb = None
                try:
                    from core import images
                    thumb = images.generate_thumbnail(
                        art.title, niche=niche, slug=art.slug
                    )
                    if thumb:
                        print(f"   🖼  썸네일 생성: {thumb.name}")
                    # (선택) 본문 스톡사진 — 영문 슬러그를 검색어로 재활용
                    photo = images.fetch_stock_photo(
                        art.slug.replace("-", " "), slug=art.slug + "-photo"
                    )
                    if photo and "<h2" in art.html:
                        # 첫 번째 h2 뒤에는 광고가 올 수 있으니 두 번째 h2 앞에 삽입
                        parts = art.html.split("<h2", 2)
                        if len(parts) >= 3:
                            img_tag = (f'<figure><img src="PHOTO_PLACEHOLDER" '
                                       f'alt="{art.primary_keyword}" loading="lazy"/></figure>')
                            art.html = parts[0] + "<h2" + parts[1] + img_tag + "<h2" + parts[2]
                            print(f"   📷 본문 사진 준비: {photo.name}")
                except Exception as e:
                    print(f"   [i] 이미지 생략({e})")
                    photo = None
                print(f"③ 발행 ({'DRY_RUN' if config.dry_run else status or config.publish_status})...")
                pub = wordpress_publisher.publish_article(
                    art, status=status, thumbnail=thumb, photo=photo
                )
                entry = {
                    "title": art.title,
                    "niche": niche,
                    "keyword": art.primary_keyword,
                    "monetization": art.monetization,
                    "result": pub,
                    "at": datetime.now().isoformat(timespec="seconds"),
                }
                results.append(entry)
                history.append(entry)
                _save_history(history)
                print(f"   ✔ {pub}")
                made += 1
            except Exception as e:
                print(f"   ✗ 실패: {e}")

    print(f"\n===== 완료: {len(results)}개 발행 =====")
    return results


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="블로그 수익화 자동 파이프라인")
    p.add_argument("--per-niche", type=int, default=1, help="니치당 글 수")
    p.add_argument("--niches", type=int, default=3, help="확정 니치 개수")
    p.add_argument("--no-naver", action="store_true", help="네이버 API 생략(Claude 추정)")
    p.add_argument("--status", default=None, help="publish|draft|future")
    args = p.parse_args()

    run_full_pipeline(
        posts_per_niche=args.per_niche,
        pick_niches=args.niches,
        use_naver=not args.no_naver,
        status=args.status,
    )
