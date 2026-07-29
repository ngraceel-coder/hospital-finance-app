"""DB 자동 백업 (계획서 10-7).

앱 시작 시 data/hospital.db 를 backup/hospital_{날짜}.db 로 복사, 30일치 보관.
하루 한 번만(같은 날짜 파일이 있으면 건너뜀).
"""
import shutil
from datetime import datetime, timedelta

from config import DB_PATH, BACKUP_DIR, BACKUP_RETENTION_DAYS
from utils.helpers import KST


def auto_backup():
    if not DB_PATH.exists():
        return None
    day = datetime.now(KST).strftime("%Y%m%d")
    dest = BACKUP_DIR / f"hospital_{day}.db"
    if not dest.exists():
        try:
            shutil.copy2(DB_PATH, dest)
        except Exception:
            return None
    _prune()
    return dest


def _prune():
    cutoff = datetime.now(KST) - timedelta(days=BACKUP_RETENTION_DAYS)
    for f in BACKUP_DIR.glob("hospital_*.db"):
        try:
            stamp = f.stem.split("_")[1]
            d = datetime.strptime(stamp, "%Y%m%d").replace(tzinfo=KST)
            if d < cutoff:
                f.unlink()
        except (IndexError, ValueError):
            continue
