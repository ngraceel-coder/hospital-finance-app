"""결제(payment) — 거래처 대금 지급 · 미결제 추적.

주의: '결제(payment)' 는 대금 지급. '결재(approval)' 와 절대 섞지 않는다.

R9. 거래처 미결제액
    = (CONFIRMED 명세서 total_amount 합계)
      − (payment_invoices.applied_amount 합계)
"""
from db.connection import transaction, cursor
from utils.helpers import now_iso, days_until

METHODS = ("계좌이체", "카드", "현금")


def invoice_paid_amount(invoice_id, conn=None):
    sql = ("SELECT COALESCE(SUM(applied_amount),0) FROM payment_invoices "
           "WHERE invoice_id = ?")
    if conn is not None:
        return int(conn.execute(sql, (invoice_id,)).fetchone()[0])
    with cursor() as c:
        return int(c.execute(sql, (invoice_id,)).fetchone()[0])


def unpaid_invoices(vendor_id=None):
    """CONFIRMED 명세서 중 미결제 잔액이 남은 건들."""
    q = """SELECT inv.id, inv.vendor_id, v.name AS vendor_name, inv.invoice_no,
                  inv.issue_date, inv.total_amount,
                  COALESCE(pi.paid, 0) AS paid_amount
           FROM invoices inv
           JOIN vendors v ON v.id = inv.vendor_id
           LEFT JOIN (SELECT invoice_id, SUM(applied_amount) AS paid
                      FROM payment_invoices GROUP BY invoice_id) pi
                 ON pi.invoice_id = inv.id
           WHERE inv.status = 'CONFIRMED'"""
    params = []
    if vendor_id:
        q += " AND inv.vendor_id = ?"; params.append(vendor_id)
    q += " ORDER BY inv.issue_date"
    with cursor() as conn:
        rows = conn.execute(q, params).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["balance"] = int(d["total_amount"]) - int(d["paid_amount"])
        if d["balance"] > 0:
            d["overdue_days"] = _overdue_days(d["issue_date"])
            out.append(d)
    return out


def _overdue_days(issue_date):
    left = days_until(issue_date)
    return -left if (left is not None and left < 0) else 0


def vendor_outstanding(vendor_id):
    """R9: 거래처 미결제 총액."""
    return sum(inv["balance"] for inv in unpaid_invoices(vendor_id))


def outstanding_by_vendor():
    """전 거래처 미결제 요약."""
    rows = unpaid_invoices()
    agg = {}
    for r in rows:
        a = agg.setdefault(r["vendor_id"], {
            "vendor_id": r["vendor_id"], "vendor_name": r["vendor_name"],
            "balance": 0, "count": 0, "max_overdue": 0})
        a["balance"] += r["balance"]
        a["count"] += 1
        a["max_overdue"] = max(a["max_overdue"], r["overdue_days"])
    return sorted(agg.values(), key=lambda x: x["balance"], reverse=True)


def total_outstanding():
    return sum(inv["balance"] for inv in unpaid_invoices())


def pay(vendor_id, allocations, handler_id, method="계좌이체", memo="", paid_at=None):
    """일괄 결제. allocations: [{invoice_id, applied_amount}].

    각 명세서 잔액을 초과 배분하지 않도록 검증한다.
    """
    allocations = [a for a in allocations if int(a.get("applied_amount", 0)) > 0]
    if not allocations:
        raise ValueError("결제할 금액이 없습니다.")
    total = sum(int(a["applied_amount"]) for a in allocations)
    with transaction() as conn:
        # 잔액 검증
        for a in allocations:
            inv = conn.execute(
                "SELECT vendor_id, total_amount, status FROM invoices WHERE id = ?",
                (a["invoice_id"],),
            ).fetchone()
            if not inv:
                raise ValueError(f"명세서 #{a['invoice_id']} 없음")
            if inv["status"] != "CONFIRMED":
                raise ValueError(f"명세서 #{a['invoice_id']} 는 확정 상태가 아닙니다.")
            if inv["vendor_id"] != vendor_id:
                raise ValueError("다른 거래처의 명세서가 섞여 있습니다.")
            paid = invoice_paid_amount(a["invoice_id"], conn=conn)
            balance = int(inv["total_amount"]) - paid
            if int(a["applied_amount"]) > balance:
                raise ValueError(
                    f"명세서 #{a['invoice_id']} 잔액({balance:,})을 초과했습니다."
                )
        cur = conn.execute(
            """INSERT INTO payments(vendor_id, paid_at, amount, method, handler_id,
                                    memo, created_at)
               VALUES(?,?,?,?,?,?,?)""",
            (vendor_id, paid_at or now_iso(), total, method, handler_id, memo,
             now_iso()),
        )
        pay_id = cur.lastrowid
        for a in allocations:
            conn.execute(
                """INSERT INTO payment_invoices(payment_id, invoice_id, applied_amount)
                   VALUES(?,?,?)""",
                (pay_id, a["invoice_id"], int(a["applied_amount"])),
            )
    return pay_id


def list_payments(vendor_id=None, limit=300):
    q = """SELECT p.*, v.name AS vendor_name, u.name AS handler_name
           FROM payments p JOIN vendors v ON v.id = p.vendor_id
           JOIN users u ON u.id = p.handler_id WHERE 1=1"""
    params = []
    if vendor_id:
        q += " AND p.vendor_id = ?"; params.append(vendor_id)
    q += " ORDER BY p.paid_at DESC LIMIT ?"; params.append(limit)
    with cursor() as conn:
        return [dict(r) for r in conn.execute(q, params).fetchall()]
