"""애플리케이션 설정.

모든 경로/상수/설정값을 한곳에서 관리한다. 환경변수(.env)로 덮어쓸 수 있다.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # dotenv 미설치 환경에서도 동작
    pass

# ── 경로 ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FILES_DIR = BASE_DIR / "files"          # 명세서 원본/보정본 보관
BACKUP_DIR = BASE_DIR / "backup"
DB_PATH = Path(os.getenv("HOSPITAL_DB_PATH", DATA_DIR / "hospital.db"))
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"

for _d in (DATA_DIR, FILES_DIR, BACKUP_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── 기관 정보 ──────────────────────────────────────────────────────────
ORG_NAME = os.getenv("ORG_NAME", "온소아청소년과의원")
ORG_UNIT = os.getenv("ORG_UNIT", "온자람실")

# ── 결재(approval) 규칙 ────────────────────────────────────────────────
# R4: 본인 발주 본인 승인 금지. 단, 원장 셀프승인 허용 여부는 설정으로 분기.
ALLOW_DIRECTOR_SELF_APPROVE = os.getenv("ALLOW_DIRECTOR_SELF_APPROVE", "1") == "1"

# 금액별 결재 분기(on/off). 켜지면 THRESHOLD 이상은 원장(position=원장) 승인 필수.
AMOUNT_BASED_APPROVAL = os.getenv("AMOUNT_BASED_APPROVAL", "0") == "1"
APPROVAL_AMOUNT_THRESHOLD = int(os.getenv("APPROVAL_AMOUNT_THRESHOLD", "500000"))

# ── 재고/유통기한 알림 ─────────────────────────────────────────────────
EXPIRY_ALERT_DAYS = int(os.getenv("EXPIRY_ALERT_DAYS", "60"))

# ── OCR / 품질 게이트 ──────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
VISION_MODEL = os.getenv("VISION_MODEL", "claude-sonnet-5")
MIN_SHORT_EDGE_PX = int(os.getenv("MIN_SHORT_EDGE_PX", "1000"))
BLUR_LAPLACIAN_MIN = float(os.getenv("BLUR_LAPLACIAN_MIN", "100"))

# ── 품목 매칭 임계값 ───────────────────────────────────────────────────
MATCH_STRONG = float(os.getenv("MATCH_STRONG", "90"))   # 단독 자동 매칭
MATCH_WEAK = float(os.getenv("MATCH_WEAK", "70"))       # 후보 제시 하한

# ── 백업 ───────────────────────────────────────────────────────────────
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

# ── 초기 관리자 계정 ───────────────────────────────────────────────────
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234")
ADMIN_NAME = os.getenv("ADMIN_NAME", "관리자")
