"""재고 관리.

R1: 재고는 계산값이다. items 테이블에 수량 컬럼을 두지 않는다.
    현재고 = SUM(stock_movements.qty)  (입고 +, 사용/폐기 -)
R10: 모든 이동에 user_id.
"""
from db.connection import cursor
from utils.helpers import now_iso, days_until
from config import EXPIRY_ALERT_DAYS

MOVE_TYPES = ("IN", "USE", "DISPOSE", "ADJUST")


def current_stock(item_id, conn=None) -> float:
    """R1: 이동 이력 합계."""
    sql = "SELECT COALESCE(SUM(qty), 0) FROM stock_movements WHERE item_id = ?"
    if conn is not None:
        return float(conn.execute(sql, (item_id,)).fetchone()[0])
    with cursor() as c:
        return float(c.execute(sql, (item_id,)).fetchone()[0])


def record_movement(item_id, move_type, qty, user_id, *, ref_type=None, ref_id=None,
                    lot_no=None, expiry_date=None, reason=None, moved_at=None,
                    conn=None):
    """재고 이동 한 건 기록.

    qty 는 호출자가 부호를 맞춰 넘긴다(입고 +, 사용/폐기 -).
    편의를 위해 move_type 에 맞춰 부호를 강제 보정한다.
    """
    if move_type not in MOVE_TYPES:
        raise ValueError(f"알 수 없는 이동 유형: {move_type}")
    qty = float(qty)
    if move_type == "IN" and qty < 0:
        qty = -qty
    elif move_type in ("USE", "DISPOSE") and qty > 0:
        qty = -qty
    # ADJUST 는 부호 그대로(±) 사용

    sql = """INSERT INTO stock_movements(item_id, move_type, qty, moved_at,
                                         ref_type, ref_id, lot_no, expiry_date,
                                         reason, user_id)
             VALUES(?,?,?,?,?,?,?,?,?,?)"""
    args = (item_id, move_type, qty, moved_at or now_iso(), ref_type, ref_id,
            lot_no, expiry_date, reason, user_id)
    if conn is not None:
        return conn.execute(sql, args).lastrowid
    with cursor() as c:
        return c.execute(sql, args).lastrowid


def use_item(item_id, qty, user_id, reason=None):
    """사용 등록(재고 차감)."""
    return record_movement(item_id, "USE", abs(float(qty)), user_id, reason=reason,
                           ref_type="MANUAL")


def dispose_item(item_id, qty, user_id, reason):
    """폐기(사유 필수)."""
    if not reason:
        raise ValueError("폐기 사유는 필수입니다.")
    return record_movement(item_id, "DISPOSE", abs(float(qty)), user_id, reason=reason,
                           ref_type="MANUAL")


def adjust_stock(item_id, target_qty, user_id, reason):
    """실사 조정: 현재고를 target_qty 로 맞추는 ADJUST 이동 생성."""
    if not reason:
        raise ValueError("실사 조정 사유는 필수입니다.")
    diff = float(target_qty) - current_stock(item_id)
    if diff == 0:
        return None
    return record_movement(item_id, "ADJUST", diff, user_id, reason=reason,
                           ref_type="MANUAL")


def stock_overview():
    """전 품목 현재고/안전재고/부족분. 활성 품목 기준."""
    with cursor() as conn:
        rows = conn.execute(
            """SELECT i.id, i.name, i.spec, i.unit, i.category, i.safety_stock,
                      i.unit_price,
                      COALESCE(SUM(sm.qty), 0) AS stock
               FROM items i
               LEFT JOIN stock_movements sm ON sm.item_id = i.id
               WHERE i.is_active = 1
               GROUP BY i.id
               ORDER BY i.category, i.name"""
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["shortage"] = max(0.0, (d["safety_stock"] or 0) - d["stock"])
        d["below_safety"] = d["stock"] < (d["safety_stock"] or 0)
        out.append(d)
    return out


def low_stock_items():
    """안전재고 미달 품목만."""
    return [r for r in stock_overview() if r["below_safety"]]


def movements_for(item_id, limit=200):
    """품목 입출고 타임라인."""
    with cursor() as conn:
        rows = conn.execute(
            """SELECT sm.*, u.name AS user_name
               FROM stock_movements sm JOIN users u ON u.id = sm.user_id
               WHERE sm.item_id = ?
               ORDER BY sm.moved_at DESC, sm.id DESC LIMIT ?""",
            (item_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def expiring_lots(days=None):
    """유통기한 임박 로트(입고분 중 남은 기한 <= days).

    로트별 현재 잔량은 단순화하여 IN 이동의 남은 기한만으로 경고한다.
    """
    days = EXPIRY_ALERT_DAYS if days is None else days
    with cursor() as conn:
        rows = conn.execute(
            """SELECT sm.item_id, i.name, i.unit, sm.lot_no, sm.expiry_date,
                      SUM(sm.qty) AS qty
               FROM stock_movements sm JOIN items i ON i.id = sm.item_id
               WHERE sm.expiry_date IS NOT NULL AND sm.expiry_date != ''
               GROUP BY sm.item_id, sm.lot_no, sm.expiry_date
               HAVING qty > 0"""
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        left = days_until(d["expiry_date"])
        if left is not None and left <= days:
            d["days_left"] = left
            out.append(d)
    return sorted(out, key=lambda x: x["days_left"])
