"""
중앙 설정 로더.
.env 파일과 환경변수에서 모든 설정을 읽어온다.
"""
import os
from pathlib import Path
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    # python-dotenv 미설치 시 시스템 환경변수만 사용
    pass


def _bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).strip().lower() in ("1", "true", "yes", "y")


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


@dataclass
class Config:
    # Claude
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")

    # 네이버 검색광고 API
    naver_ad_api_key: str = os.getenv("NAVER_AD_API_KEY", "")
    naver_ad_secret_key: str = os.getenv("NAVER_AD_SECRET_KEY", "")
    naver_ad_customer_id: str = os.getenv("NAVER_AD_CUSTOMER_ID", "")

    # 워드프레스
    wp_url: str = os.getenv("WP_URL", "").rstrip("/")
    wp_username: str = os.getenv("WP_USERNAME", "")
    wp_app_password: str = os.getenv("WP_APP_PASSWORD", "")

    # 수익화
    adsense_client_id: str = os.getenv("ADSENSE_CLIENT_ID", "")
    adsense_slot_id: str = os.getenv("ADSENSE_SLOT_ID", "")
    coupang_partners_tag: str = os.getenv("COUPANG_PARTNERS_TAG", "")
    pexels_api_key: str = os.getenv("PEXELS_API_KEY", "")

    # 운영
    posts_per_day: int = _int("POSTS_PER_DAY", 3)
    publish_status: str = os.getenv("PUBLISH_STATUS", "draft")
    dry_run: bool = _bool("DRY_RUN", True)

    # 경로
    base_dir: Path = Path(__file__).parent
    output_dir: Path = Path(__file__).parent / "data" / "output"

    def ensure_dirs(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate(self, need=("claude",)) -> list:
        """필요한 자격증명이 채워졌는지 확인. 누락 항목 리스트 반환."""
        missing = []
        checks = {
            "claude": [("ANTHROPIC_API_KEY", self.anthropic_api_key)],
            "naver": [
                ("NAVER_AD_API_KEY", self.naver_ad_api_key),
                ("NAVER_AD_SECRET_KEY", self.naver_ad_secret_key),
                ("NAVER_AD_CUSTOMER_ID", self.naver_ad_customer_id),
            ],
            "wordpress": [
                ("WP_URL", self.wp_url),
                ("WP_USERNAME", self.wp_username),
                ("WP_APP_PASSWORD", self.wp_app_password),
            ],
        }
        for group in need:
            for name, val in checks.get(group, []):
                if not val:
                    missing.append(name)
        return missing


config = Config()
config.ensure_dirs()
