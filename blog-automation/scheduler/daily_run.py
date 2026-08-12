"""
매일 자동 실행 스케줄러.

두 가지 방법:
  1) cron (권장, 서버): 아래 run_once()를 크론이 매일 호출
        0 9 * * *  cd /path/blog-automation && python scheduler/daily_run.py
  2) 상주 프로세스: python scheduler/daily_run.py --loop
        (schedule 라이브러리로 매일 정해진 시각에 실행)
"""
from __future__ import annotations
import sys
from pathlib import Path

# 프로젝트 루트를 import 경로에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import config
from core.pipeline import run_full_pipeline


def run_once():
    """하루치 발행 (POSTS_PER_DAY 를 3개 니치에 분배)."""
    per_niche = max(1, config.posts_per_day // 3)
    print(f"[daily_run] {config.posts_per_day}개 목표 · 니치당 {per_niche}개")
    return run_full_pipeline(posts_per_niche=per_niche, pick_niches=3)


def loop(at_time: str = "09:00"):
    """상주 모드: 매일 지정 시각에 실행."""
    try:
        import schedule
    except ImportError:
        print("schedule 패키지가 필요합니다: pip install schedule")
        sys.exit(1)
    import time

    schedule.every().day.at(at_time).do(run_once)
    print(f"[daily_run] 매일 {at_time} 자동 실행 대기 중... (Ctrl+C 종료)")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    if "--loop" in sys.argv:
        loop()
    else:
        run_once()
