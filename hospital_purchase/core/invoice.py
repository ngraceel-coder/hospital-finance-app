"""거래명세서 처리 · 3-way 매칭 · 확정(입고 반영).

핵심 규칙:
  R2  status != APPROVED/RECEIVING 인 발주에는 명세서를 연결할 수 없다.
  R7  OCR 결과는 자동 확정하지 않는다. 사람이 확정 버튼을 눌러야 재고 반영.
  R8  확정은 1회성. 잘못 확정 시 역분개(ADJUST) 로만 취소.
  R10 모든 행위에 user_id.

확정은 여러 테이블(stock_movements, po_items, invoices, item_aliases)을
건드리므로 반드시 하나의 트랜잭션으로 묶는다(계획서 10-4).
"""
from db.connection import transaction, cursor
from db.queries import log_action, get_item, set_item_price
from core import inventory, matching
from core.purchase import RECEIVABLE_STATES, refresh_receiving_status
from utils.helpers import now_iso

# 3-way 매칭 신호등
GREEN, YELLOW, RED = "🟢", "🟡", "🔴"


def create_invoice(vendor_id, original_file, handler_id, *, invoice_no=None,
                   issue_date=None, po_id=None, processed_file=None, ocr_raw=None,
                   total_amount=0, ocr_items=None):
    """명세서 초안 생성(PENDING_REVIEW). ocr_items 는 매칭 후 invoice_items 로 저장.

    ocr_items: [{ocr_item_name, item_id, qty, unit_price, amount, lot_no,
                 expiry_date, match_status}]
    """
    if po_id is not None:
        _assert_receivable(po_id)
    with transaction() as conn:
        cur = conn.execute(
            """INSERT INTO invoices(vendor_id, invoice_no, issue_date, po_id,
                   original_file, processed_file, ocr_raw, status, total_amount,
                   handler_id, created_at)
               VALUES(?,?,?,?,?,?,?, 'PENDING_REVIEW', ?, ?, ?)""",
            (vendor_id, invoice_no, issue_date, po_id, original_file, processed_file,
             ocr_raw, int(total_amount or 0), handler_id, now_iso()),
        )
        inv_id = cur.lastrowid
        for it in (ocr_items or []):
            conn.execute(
                """INSERT INTO invoice_items(invoice_id, ocr_item_name, item_id, qty,
                       unit_price, amount, lot_no, expiry_date, match_status)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (inv_id, it.get("ocr_item_name", ""), it.get("item_id"),
                 float(it.get("qty", 0)), int(it.get("unit_price", 0)),
                 int(it.get("amount", 0)), it.get("lot_no"), it.get("expiry_date"),
                 it.get("match_status", "UNMATCHED")),
            )
        log_action("INVOICE", inv_id, "REQUEST", handler_id, conn=conn)
    return inv_id


def _assert_receivable(po_id):
    """R2: 승인된 발주에만 연결 가능."""
    with cursor() as conn:
        r = conn.execute(
            "SELECT status FROM purchase_orders WHERE id = ?", (po_id,)
        ).fetchone()
    if not r:
        raise ValueError("발주를 찾을 수 없습니다.")
    if r["status"] not in RECEIVABLE_STATES:
        raise ValueError(
            f"승인된 발주에만 명세서를 연결할 수 있습니다. (현재: {r['status']})"
        )


def update_invoice_items(inv_id, items):
    """검수 화면에서 수정한 행들을 저장(PENDING_REVIEW 상태에서만)."""
    inv = get_invoice(inv_id)
    if not inv:
        raise ValueError("명세서를 찾을 수 없습니다.")
    if inv["status"] != "PENDING_REVIEW":
        raise ValueError("검수 대기 상태에서만 수정할 수 있습니다.")
    total = sum(int(it.get("amount", 0)) for it in items)
    with transaction() as conn:
        conn.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (inv_id,))
        for it in items:
            conn.execute(
                """INSERT INTO invoice_items(invoice_id, ocr_item_name, item_id, qty,
                       unit_price, amount, lot_no, expiry_date, match_status)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (inv_id, it.get("ocr_item_name", ""), it.get("item_id"),
                 float(it.get("qty", 0)), int(it.get("unit_price", 0)),
                 int(it.get("amount", 0)), it.get("lot_no"), it.get("expiry_date"),
                 it.get("match_status", "UNMATCHED")),
            )
        conn.execute("UPDATE invoices SET total_amount = ? WHERE id = ?",
                     (total, inv_id))


def three_way(inv_id):
    """3-way 매칭 (계획서 6.5). 발주 ↔ 명세서 수량 비교.

    반환: {lines: [...행별 신호등...], blockers: [문자열], can_confirm: bool}
    """
    inv = get_invoice(inv_id)
    items = get_invoice_items(inv_id)
    po_items = {}
    if inv and inv["po_id"]:
        for pi in _po_items_map(inv["po_id"]):
            po_items[pi["item_id"]] = pi

    lines, blockers = [], []
    for it in items:
        signal, note = GREEN, ""
        iid = it["item_id"]
        if iid is None:
            signal, note = RED, "미매칭 품목 (신규 등록 또는 행 제외 필요)"
            blockers.append(f"{it['ocr_item_name']}: 품목 미매칭")
        elif inv and inv["po_id"] and iid not in po_items:
            signal, note = RED, "발주에 없는 품목"
            blockers.append(f"{it['ocr_item_name']}: 발주에 없는 품목")
        elif inv and inv["po_id"] and iid in po_items:
            po = po_items[iid]
            remaining = po["qty"] - po["received_qty"]
            if it["qty"] > remaining + 1e-9:
                signal, note = RED, f"발주 잔량 초과(잔량 {remaining:g})"
                blockers.append(f"{it['ocr_item_name']}: 명세서 수량 > 발주 잔량")
            elif it["qty"] < remaining - 1e-9:
                signal, note = YELLOW, f"부분입고(잔량 {remaining - it['qty']:g})"
            # 단가 불일치
            if it["unit_price"] and po["unit_price"] and it["unit_price"] != po["unit_price"]:
                if signal == GREEN:
                    signal = YELLOW
                note = (note + " / " if note else "") + \
                    f"단가 불일치(발주 {po['unit_price']:,} vs 명세서 {it['unit_price']:,})"
        else:
            # 연결된 발주 없음 → 직접구매(사유 필요) 이지만 확정은 가능
            signal = YELLOW
            note = "발주 없는 직접 구매"
        d = dict(it); d["signal"] = signal; d["note"] = note
        lines.append(d)

    return {"lines": lines, "blockers": blockers, "can_confirm": len(blockers) == 0}


def confirm(inv_id, handler_id, *, update_prices=False, direct_reason=None):
    """명세서 확정 → 재고 반영(R7). 하나의 트랜잭션.

    - 각 invoice_item(매칭된 것) → stock_movements IN
    - po_items.received_qty 누적 → 발주 상태 갱신
    - 별칭 학습(item_aliases)
    - 단가 갱신 옵션(items.unit_price)
    R8: 이미 CONFIRMED 면 거부.
    """
    inv = get_invoice(inv_id)
    if not inv:
        raise ValueError("명세서를 찾을 수 없습니다.")
    if inv["status"] != "PENDING_REVIEW":
        raise ValueError("검수 대기 상태만 확정할 수 있습니다.")

    tw = three_way(inv_id)
    if not tw["can_confirm"]:
        raise ValueError("확정 차단: " + "; ".join(tw["blockers"]))

    items = get_invoice_items(inv_id)
    if inv["po_id"] is None and not direct_reason:
        # 발주 없는 직접구매는 사유 필요(6.5)
        direct_reason = "발주 없는 직접 구매"

    with transaction() as conn:
        for it in items:
            iid = it["item_id"]
            if iid is None:
                continue
            # 입고 이동
            inventory.record_movement(
                iid, "IN", it["qty"], handler_id,
                ref_type="INVOICE", ref_id=inv_id,
                lot_no=it["lot_no"], expiry_date=it["expiry_date"],
                reason=direct_reason, conn=conn,
            )
            # 발주 잔량 갱신
            if inv["po_id"]:
                conn.execute(
                    """UPDATE po_items SET received_qty = received_qty + ?
                       WHERE po_id = ? AND item_id = ?""",
                    (it["qty"], inv["po_id"], iid),
                )
            # 별칭 학습
            if it["ocr_item_name"]:
                conn.execute(
                    """INSERT OR IGNORE INTO item_aliases(item_id, vendor_id,
                           alias_text, created_at) VALUES(?,?,?,?)""",
                    (iid, inv["vendor_id"], it["ocr_item_name"].strip(), now_iso()),
                )
            # 단가 갱신
            if update_prices and it["unit_price"]:
                conn.execute("UPDATE items SET unit_price = ? WHERE id = ?",
                             (int(it["unit_price"]), iid))

        conn.execute(
            "UPDATE invoices SET status = 'CONFIRMED', confirmed_at = ?, handler_id = ? "
            "WHERE id = ?",
            (now_iso(), handler_id, inv_id),
        )
        if inv["po_id"]:
            refresh_receiving_status(inv["po_id"], conn=conn)
        log_action("INVOICE", inv_id, "CONFIRM", handler_id, conn=conn)
    return True


def reject(inv_id, handler_id, reason):
    """검수 반려."""
    if not reason:
        raise ValueError("반려 사유는 필수입니다.")
    inv = get_invoice(inv_id)
    if not inv or inv["status"] != "PENDING_REVIEW":
        raise ValueError("검수 대기 상태만 반려할 수 있습니다.")
    with transaction() as conn:
        conn.execute("UPDATE invoices SET status = 'REJECTED' WHERE id = ?", (inv_id,))
        log_action("INVOICE", inv_id, "REJECT", handler_id, comment=reason, conn=conn)


def reverse_confirmed(inv_id, handler_id, reason):
    """R8: 잘못 확정한 명세서 취소 → 역분개(ADJUST) 이동 생성.

    입고분을 음수 ADJUST 로 상쇄하고 received_qty 를 되돌린다.
    명세서 자체는 CONFIRMED 이력을 남기되 status='REJECTED' 로 표시.
    """
    if not reason:
        raise ValueError("취소 사유는 필수입니다.")
    inv = get_invoice(inv_id)
    if not inv or inv["status"] != "CONFIRMED":
        raise ValueError("확정된 명세서만 취소할 수 있습니다.")
    items = get_invoice_items(inv_id)
    with transaction() as conn:
        for it in items:
            iid = it["item_id"]
            if iid is None:
                continue
            inventory.record_movement(
                iid, "ADJUST", -float(it["qty"]), handler_id,
                ref_type="INVOICE", ref_id=inv_id,
                reason=f"명세서#{inv_id} 확정취소: {reason}", conn=conn,
            )
            if inv["po_id"]:
                conn.execute(
                    """UPDATE po_items SET received_qty = MAX(0, received_qty - ?)
                       WHERE po_id = ? AND item_id = ?""",
                    (it["qty"], inv["po_id"], iid),
                )
        conn.execute(
            "UPDATE invoices SET status = 'REJECTED' WHERE id = ?", (inv_id,)
        )
        log_action("INVOICE", inv_id, "CANCEL", handler_id, comment=reason, conn=conn)


# ── 조회 ───────────────────────────────────────────────────────────────
def get_invoice(inv_id):
    with cursor() as conn:
        r = conn.execute(
            """SELECT inv.*, v.name AS vendor_name, u.name AS handler_name,
                      po.po_number
               FROM invoices inv
               JOIN vendors v ON v.id = inv.vendor_id
               LEFT JOIN users u ON u.id = inv.handler_id
               LEFT JOIN purchase_orders po ON po.id = inv.po_id
               WHERE inv.id = ?""",
            (inv_id,),
        ).fetchone()
    return dict(r) if r else None


def get_invoice_items(inv_id):
    with cursor() as conn:
        rows = conn.execute(
            """SELECT ii.*, i.name AS item_name, i.spec, i.unit
               FROM invoice_items ii LEFT JOIN items i ON i.id = ii.item_id
               WHERE ii.invoice_id = ? ORDER BY ii.id""",
            (inv_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_invoices(status=None, vendor_id=None, limit=500):
    q = """SELECT inv.*, v.name AS vendor_name
           FROM invoices inv JOIN vendors v ON v.id = inv.vendor_id WHERE 1=1"""
    params = []
    if status:
        q += " AND inv.status = ?"; params.append(status)
    if vendor_id:
        q += " AND inv.vendor_id = ?"; params.append(vendor_id)
    q += " ORDER BY inv.created_at DESC LIMIT ?"; params.append(limit)
    with cursor() as conn:
        return [dict(r) for r in conn.execute(q, params).fetchall()]


def pending_review_count():
    with cursor() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM invoices WHERE status = 'PENDING_REVIEW'"
        ).fetchone()[0]


def _po_items_map(po_id):
    with cursor() as conn:
        rows = conn.execute(
            "SELECT item_id, qty, received_qty, unit_price FROM po_items WHERE po_id = ?",
            (po_id,),
        ).fetchall()
    return [dict(r) for r in rows]
