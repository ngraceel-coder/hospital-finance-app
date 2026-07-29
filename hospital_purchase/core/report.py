"""집계 · 리포트 (거래처별 월별 현황, 단가 추이, 지출).

엑셀 내보내기는 utils/excel.py 가 담당한다. 여기서는 순수 집계만.
"""
from db.connection import cursor
from utils.helpers import month_key


def vendor_monthly_matrix():
    """행: 거래처, 열: 월(YYYY-MM), 값: CONFIRMED 명세서 total_amount 합계.

    반환: {"months": [...], "rows": [{vendor_id, vendor_name, cells:{month: amt},
            total}]}
    """
    with cursor() as conn:
        rows = conn.execute(
            """SELECT inv.vendor_id, v.name AS vendor_name, inv.issue_date,
                      inv.created_at, inv.total_amount
               FROM invoices inv JOIN vendors v ON v.id = inv.vendor_id
               WHERE inv.status = 'CONFIRMED'"""
        ).fetchall()
    months = set()
    agg = {}
    for r in rows:
        m = month_key(r["issue_date"] or r["created_at"])
        months.add(m)
        a = agg.setdefault(r["vendor_id"], {
            "vendor_id": r["vendor_id"], "vendor_name": r["vendor_name"],
            "cells": {}, "total": 0})
        a["cells"][m] = a["cells"].get(m, 0) + int(r["total_amount"] or 0)
        a["total"] += int(r["total_amount"] or 0)
    return {
        "months": sorted(m for m in months if m),
        "rows": sorted(agg.values(), key=lambda x: x["vendor_name"]),
    }


def monthly_spend():
    """월별 총 입고액(CONFIRMED 명세서 기준)."""
    matrix = vendor_monthly_matrix()
    out = {m: 0 for m in matrix["months"]}
    for row in matrix["rows"]:
        for m, v in row["cells"].items():
            out[m] = out.get(m, 0) + v
    return dict(sorted(out.items()))


def spend_this_month():
    from utils.helpers import today_iso

    m = today_iso()[:7]
    return monthly_spend().get(m, 0)


def price_history(item_id):
    """품목 단가 추이(확정 명세서의 단가)."""
    with cursor() as conn:
        rows = conn.execute(
            """SELECT inv.issue_date, inv.created_at, ii.unit_price, v.name AS vendor_name
               FROM invoice_items ii
               JOIN invoices inv ON inv.id = ii.invoice_id
               JOIN vendors v ON v.id = inv.vendor_id
               WHERE ii.item_id = ? AND inv.status = 'CONFIRMED'
               ORDER BY inv.issue_date, inv.created_at""",
            (item_id,),
        ).fetchall()
    return [{"date": (r["issue_date"] or r["created_at"] or "")[:10],
             "unit_price": int(r["unit_price"] or 0),
             "vendor_name": r["vendor_name"]} for r in rows]


def vendor_cards():
    """거래처별 현황 카드 데이터(이번 달 입고 건수/총액, 미결제, 최근 거래일)."""
    from core.payment import vendor_outstanding
    from utils.helpers import today_iso

    this_month = today_iso()[:7]
    with cursor() as conn:
        vendors = conn.execute(
            "SELECT id, name FROM vendors WHERE is_active = 1 ORDER BY name"
        ).fetchall()
        out = []
        for v in vendors:
            invs = conn.execute(
                """SELECT issue_date, created_at, total_amount
                   FROM invoices WHERE vendor_id = ? AND status = 'CONFIRMED'""",
                (v["id"],),
            ).fetchall()
            this_cnt = this_amt = 0
            last_date = ""
            for inv in invs:
                d = (inv["issue_date"] or inv["created_at"] or "")[:10]
                last_date = max(last_date, d)
                if d[:7] == this_month:
                    this_cnt += 1
                    this_amt += int(inv["total_amount"] or 0)
            out.append({
                "vendor_id": v["id"], "vendor_name": v["name"],
                "month_count": this_cnt, "month_amount": this_amt,
                "outstanding": vendor_outstanding(v["id"]),
                "last_date": last_date or "-",
            })
    return out


def monthly_usage(item_id):
    """품목 월별 사용량(USE, 절대값)."""
    with cursor() as conn:
        rows = conn.execute(
            """SELECT moved_at, qty FROM stock_movements
               WHERE item_id = ? AND move_type = 'USE'""",
            (item_id,),
        ).fetchall()
    agg = {}
    for r in rows:
        m = month_key(r["moved_at"])
        agg[m] = agg.get(m, 0) + abs(float(r["qty"]))
    return dict(sorted(agg.items()))


def recent_activity(limit=10):
    """최근 활동(결재이력 + 결제) 통합 타임라인."""
    with cursor() as conn:
        logs = conn.execute(
            """SELECT l.acted_at AS ts, l.doc_type, l.doc_id, l.action,
                      u.name AS user_name
               FROM approval_logs l JOIN users u ON u.id = l.user_id
               ORDER BY l.acted_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in logs]
