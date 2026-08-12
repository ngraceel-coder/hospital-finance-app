#!/usr/bin/env python3
"""
블로그 수익화 자동화 - 통합 CLI 진입점.

명령:
  python run.py check       # 설정/자격증명 상태 점검
  python run.py research     # 키워드 조사만 (네이버 API)
  python run.py topics       # 니치 조사 + 주제 5개→3개 선정 (발행 안 함)
  python run.py generate     # 주제 하나로 글 1개 생성 (발행 안 함, 미리보기)
  python run.py run          # 전체 파이프라인 (조사→생성→발행)
  python run.py daily        # 하루치 자동 발행 (스케줄러가 호출하는 것과 동일)
"""
import sys
import json

from config import config


def cmd_check():
    print("=== 설정 점검 ===")
    groups = {
        "Claude (콘텐츠 생성)": "claude",
        "네이버 검색광고 (키워드 조사)": "naver",
        "워드프레스 (발행)": "wordpress",
    }
    for label, key in groups.items():
        missing = config.validate(need=(key,))
        status = "✅ 준비됨" if not missing else f"❌ 누락: {', '.join(missing)}"
        print(f"  {label:<28} {status}")
    print(f"\n  DRY_RUN = {config.dry_run}  (True면 실제 발행 안 함)")
    print(f"  PUBLISH_STATUS = {config.publish_status}")
    print(f"  POSTS_PER_DAY = {config.posts_per_day}")
    print(f"  CLAUDE_MODEL = {config.claude_model}")


def cmd_research():
    from core.keyword_research import research_niche, NICHE_SEEDS
    for niche in NICHE_SEEDS:
        print(f"\n=== [{niche}] ===")
        try:
            for r in research_niche(niche, top_n=10):
                print(f"  {r['score']:>6.1f}  {r['keyword']:<20} "
                      f"검색량 {r['total_search']:>7,}  경쟁 {r['competition']}")
        except Exception as e:
            print(f"  오류: {e}")


def cmd_topics():
    from core.topic_selector import select_top_niches
    from core.keyword_research import NICHE_SEEDS
    niches = list(NICHE_SEEDS.keys())
    use_naver = not config.validate(need=("naver",))
    res = select_top_niches(niches, pick=3, use_naver=use_naver)
    print("\n=== 확정 니치 TOP 3 ===")
    for n in res["chosen_niches"]:
        print(f"\n▶ {n} (점수 {res['niche_scores'][n]:.1f})")
        for c in res["candidates"][n][:5]:
            print(f"   - {c['title']}")
            print(f"     키워드: {c['primary_keyword']} · {c['monetization']} · {c['est_score']}")
    out = config.output_dir / "topics.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {out}")


def cmd_generate():
    from core.content_generator import generate_article, quality_gate
    from core import monetization
    title = sys.argv[2] if len(sys.argv) > 2 else "2025 근로장려금 신청 자격과 지급일 총정리"
    keyword = sys.argv[3] if len(sys.argv) > 3 else "근로장려금 신청 자격"
    art = generate_article(title, keyword, niche="정부지원금", monetization="adsense")
    art.html = monetization.inject(art.html, art.monetization, keyword)
    ok, probs = quality_gate(art)
    fname = config.output_dir / f"preview_{art.slug}.html"
    fname.write_text(art.html, encoding="utf-8")
    print(f"제목: {art.title}\n글자수: {art.word_count} · 통과:{ok} {probs}")
    print(f"저장: {fname}")


def cmd_run():
    from core.pipeline import run_full_pipeline
    use_naver = not config.validate(need=("naver",))
    run_full_pipeline(posts_per_niche=1, pick_niches=3, use_naver=use_naver)


def cmd_daily():
    from scheduler.daily_run import run_once
    run_once()


COMMANDS = {
    "check": cmd_check,
    "research": cmd_research,
    "topics": cmd_topics,
    "generate": cmd_generate,
    "run": cmd_run,
    "daily": cmd_daily,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(0 if len(sys.argv) < 2 else 1)
    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
