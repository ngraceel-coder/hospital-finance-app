"""날짜·금액 포맷, 공통 유틸.

- 날짜는 ISO 8601 문자열로 통일(계획서 10-1). SQLite에 DATE 타입 없음.
- 금액은 정수(원). float 금지(계획서 10-2).
"""
from datetime import datetime, date, timezone, timedelta

# 한국 표준시
KST = timezone(timedelta(hours=9))


def now_iso() -> str:
    """현재 시각 ISO 8601 문자열 (초 단위)."""
    return datetime.now(KST).replace(microsecond=0).isoformat()


def today_iso() -> str:
    return datetime.now(KST).date().isoformat()


def parse_iso(s: str):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d")
        except ValueError:
            return None


def fmt_won(amount) -> str:
    """정수 금액을 '1,200원' 형태로."""
    try:
        return f"{int(round(amount)):,}원"
    except (TypeError, ValueError):
        return "-"


def fmt_qty(qty) -> str:
    """수량은 REAL. 정수면 정수로, 소수면 소수로 표시."""
    try:
        f = float(qty)
    except (TypeError, ValueError):
        return "-"
    return str(int(f)) if f.is_integer() else f"{f:g}"


def parse_amount(s) -> int:
    """'1,200원', '₩1200', '1200' → 1200. 실패 시 0."""
    if s is None:
        return 0
    if isinstance(s, (int, float)):
        return int(round(s))
    digits = "".join(ch for ch in str(s) if ch.isdigit() or ch == "-")
    if digits in ("", "-"):
        return 0
    return int(digits)


def days_until(iso_date: str):
    """오늘부터 대상일까지 남은 일수. 음수면 지난 것."""
    d = parse_iso(iso_date)
    if not d:
        return None
    return (d.date() - datetime.now(KST).date()).days


def month_key(iso: str) -> str:
    """ISO 문자열 → 'YYYY-MM'."""
    d = parse_iso(iso)
    return d.strftime("%Y-%m") if d else ""


def new_po_number(seq: int, day: str = None) -> str:
    """PO-YYYYMMDD-NNN."""
    day = day or datetime.now(KST).strftime("%Y%m%d")
    return f"PO-{day}-{seq:03d}"
