"""발주(purchase order) 생성 · 상태 전이 · 결재(approval).

주의: 여기서 다루는 것은 '결재(approval)' — 원장이 발주를 승인하는 행위다.
'결제(payment)' — 대금 지급 — 은 core/payment.py 에 있다. 절대 섞지 않는다.

상태 전이 (계획서 3.2):
  DRAFT → PENDING → APPROVED → RECEIVING → CLOSED
              ↘ REJECTED → PENDING(재요청)
          (PENDING/APPROVED) → CANCELED

핵심 규칙:
  R3  승인된(APPROVED 이후) 발주는 수정 불가 → 취소 후 재발주.
  R4  본인 발주 본인 승인 금지(원장 셀프승인은 설정으로 허용).
  R5  결재는 체크만. 승인 시 approver_id, approved_at 자동 기록.
  R10 모든 행위에 user_id → approval_logs.
"""
from db.connection import transaction, cursor
from db.queries import log_action, get_vendor, get_item
from utils.helpers import now_iso
from config import (
    ALLOW_DIRECTOR_SELF_APPROVE,
    AMOUNT_BASED_APPROVAL,
    APPROVAL_AMOUNT_THRESHOLD,
)

# 허용 상태 전이 표
_TRANSITIONS = {
    "DRAFT": {"PENDING", "CANCELED"},
    "PENDING": {"APPROVED", "REJECTED", "CANCELED"},
    "APPROVED": {"RECEIVING", "CLOSED", "CANCELED"},
    "REJECTED": {"PENDING"},          # 재요청
    "RECEIVING": {"CLOSED", "CANCELED"},
    "CLOSED": set(),
    "CANCELED": set(),
}

# 명세서 연결 가능 상태 (R2)
RECEIVABLE_STATES = ("APPROVED", "RECEIVING")


def _next_po_seq(conn, day):
    """당일 발주 일련번호."""
    prefix = f"PO-{day}-"
    row = conn.execute(
        "SELECT po_number FROM purchase_orders WHERE po_number LIKE ? "
        "ORDER BY po_number DESC LIMIT 1",
        (prefix + "%",),
    ).fetchone()
    if not row:
        return 1
    return int(row["po_number"].split("-")[-1]) + 1


def create_po(vendor_id, requester_id, lines, memo="", submit=False):
    """발주 생성.

    lines: [{item_id, qty, unit_price}] — amount 는 자동 계산.
    submit=False → DRAFT(임시저장), True → PENDING(결재요청).
    """
    if not lines:
        raise ValueError("발주 품목이 없습니다.")
    day = now_iso()[:10].replace("-", "")
    status = "PENDING" if submit else "DRAFT"
    with transaction() as conn:
        seq = _next_po_seq(conn, day)
        po_number = f"PO-{day}-{seq:03d}"
        total = 0
        for ln in lines:
            total += int(ln["qty"] * ln["unit_price"])
        cur = conn.execute(
            """INSERT INTO purchase_orders(po_number, vendor_id, requester_id,
                   requested_at, status, total_amount, memo)
               VALUES(?,?,?,?,?,?,?)""",
            (po_number, vendor_id, requester_id, now_iso(), status, total, memo),
        )
        po_id = cur.lastrowid
        for ln in lines:
            amount = int(ln["qty"] * ln["unit_price"])
            conn.execute(
                """INSERT INTO po_items(po_id, item_id, qty, unit_price, amount)
                   VALUES(?,?,?,?,?)""",
                (po_id, ln["item_id"], float(ln["qty"]), int(ln["unit_price"]), amount),
            )
        action = "REQUEST" if submit else "DRAFT"
        log_action("PO", po_id, action, requester_id, conn=conn)
    return po_id


def update_draft(po_id, lines, memo=""):
    """DRAFT 상태에서만 내용 수정 가능(R3: APPROVED 이후 수정 불가)."""
    po = get_po(po_id)
    if not po:
        raise ValueError("발주를 찾을 수 없습니다.")
    if po["status"] not in ("DRAFT", "REJECTED"):
        raise ValueError("임시저장/반려 상태의 발주만 수정할 수 있습니다.")
    total = sum(int(ln["qty"] * ln["unit_price"]) for ln in lines)
    with transaction() as conn:
        conn.execute("DELETE FROM po_items WHERE po_id = ?", (po_id,))
        for ln in lines:
            amount = int(ln["qty"] * ln["unit_price"])
            conn.execute(
                """INSERT INTO po_items(po_id, item_id, qty, unit_price, amount)
                   VALUES(?,?,?,?,?)""",
                (po_id, ln["item_id"], float(ln["qty"]), int(ln["unit_price"]), amount),
            )
        conn.execute(
            "UPDATE purchase_orders SET total_amount = ?, memo = ? WHERE id = ?",
            (total, memo, po_id),
        )


def _transition(po_id, to_status, user_id, action, *, comment="", extra_sets=None):
    po = get_po(po_id)
    if not po:
        raise ValueError("발주를 찾을 수 없습니다.")
    frm = po["status"]
    if to_status not in _TRANSITIONS.get(frm, set()):
        raise ValueError(f"'{frm}' → '{to_status}' 상태 전이는 허용되지 않습니다.")
    sets = {"status": to_status}
    if extra_sets:
        sets.update(extra_sets)
    cols = ", ".join(f"{k} = ?" for k in sets)
    with transaction() as conn:
        conn.execute(
            f"UPDATE purchase_orders SET {cols} WHERE id = ?",
            (*sets.values(), po_id),
        )
        log_action("PO", po_id, action, user_id, comment=comment, conn=conn)
    return po


def submit(po_id, user_id):
    """임시저장/반려 → 결재요청."""
    po = get_po(po_id)
    action = "RESUBMIT" if po and po["status"] == "REJECTED" else "REQUEST"
    return _transition(po_id, "PENDING", user_id, action)


def approve(approver, po_id, comment=""):
    """R4·R5: 승인. approver 는 사용자 dict.

    - 결재 권한(APPROVER 이상) 필요.
    - 본인 발주 본인 승인 금지. 단, 원장(position=원장) 셀프승인은 설정으로 허용.
    - 금액별 분기(설정 on): 임계액 이상은 원장만 승인 가능.
    """
    from core.auth import can_approve

    po = get_po(po_id)
    if not po:
        raise ValueError("발주를 찾을 수 없습니다.")
    if po["status"] != "PENDING":
        raise ValueError("승인 대기(PENDING) 상태만 승인할 수 있습니다.")
    if not can_approve(approver):
        raise ValueError("결재 권한이 없습니다.")

    # R4: 셀프 승인 차단
    if po["requester_id"] == approver["id"]:
        is_director = approver.get("position") == "원장"
        if not (is_director and ALLOW_DIRECTOR_SELF_APPROVE):
            raise ValueError("본인이 요청한 발주는 본인이 승인할 수 없습니다.")

    # 금액별 결재 분기
    if AMOUNT_BASED_APPROVAL and po["total_amount"] >= APPROVAL_AMOUNT_THRESHOLD:
        if approver.get("position") != "원장":
            raise ValueError(
                f"{APPROVAL_AMOUNT_THRESHOLD:,}원 이상 발주는 원장 승인이 필요합니다."
            )

    return _transition(
        po_id, "APPROVED", approver["id"], "APPROVE", comment=comment,
        extra_sets={"approver_id": approver["id"], "approved_at": now_iso(),
                    "reject_reason": None},
    )


def reject(approver, po_id, reason):
    """반려(사유 필수)."""
    from core.auth import can_approve

    if not reason:
        raise ValueError("반려 사유는 필수입니다.")
    if not can_approve(approver):
        raise ValueError("결재 권한이 없습니다.")
    return _transition(
        po_id, "REJECTED", approver["id"], "REJECT", comment=reason,
        extra_sets={"reject_reason": reason},
    )


def cancel(po_id, user_id, reason=""):
    """취소(DRAFT/PENDING/APPROVED/RECEIVING)."""
    return _transition(po_id, "CANCELED", user_id, "CANCEL", comment=reason)


def refresh_receiving_status(po_id, conn=None):
    """입고 반영 후 발주 상태 갱신.

    po_items.received_qty 합계가 발주 수량을 모두 채우면 CLOSED, 일부면 RECEIVING.
    (명세서 확정 트랜잭션 안에서 conn 을 받아 호출된다.)
    """
    own = conn is None
    if own:
        conn = transaction().__enter__()  # pragma: no cover - 편의 경로
    try:
        rows = conn.execute(
            "SELECT qty, received_qty FROM po_items WHERE po_id = ?", (po_id,)
        ).fetchall()
        if not rows:
            return
        fully = all(r["received_qty"] >= r["qty"] for r in rows)
        any_recv = any(r["received_qty"] > 0 for r in rows)
        cur = conn.execute(
            "SELECT status FROM purchase_orders WHERE id = ?", (po_id,)
        ).fetchone()
        status = cur["status"]
        new = status
        if status in ("APPROVED", "RECEIVING"):
            new = "CLOSED" if fully else ("RECEIVING" if any_recv else status)
        if new != status:
            conn.execute(
                "UPDATE purchase_orders SET status = ? WHERE id = ?", (new, po_id)
            )
    finally:
        if own:
            conn.commit()
            conn.close()


# ── 조회 ───────────────────────────────────────────────────────────────
def get_po(po_id):
    with cursor() as conn:
        r = conn.execute(
            """SELECT po.*, v.name AS vendor_name, u.name AS requester_name,
                      a.name AS approver_name
               FROM purchase_orders po
               JOIN vendors v ON v.id = po.vendor_id
               JOIN users u ON u.id = po.requester_id
               LEFT JOIN users a ON a.id = po.approver_id
               WHERE po.id = ?""",
            (po_id,),
        ).fetchone()
    return dict(r) if r else None


def get_po_items(po_id):
    with cursor() as conn:
        rows = conn.execute(
            """SELECT pi.*, i.name AS item_name, i.spec, i.unit
               FROM po_items pi JOIN items i ON i.id = pi.item_id
               WHERE pi.po_id = ? ORDER BY pi.id""",
            (po_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_pos(status=None, requester_id=None, vendor_id=None, limit=500):
    q = """SELECT po.*, v.name AS vendor_name, u.name AS requester_name
           FROM purchase_orders po
           JOIN vendors v ON v.id = po.vendor_id
           JOIN users u ON u.id = po.requester_id WHERE 1=1"""
    params = []
    if status:
        if isinstance(status, (list, tuple)):
            q += f" AND po.status IN ({','.join('?' * len(status))})"
            params += list(status)
        else:
            q += " AND po.status = ?"; params.append(status)
    if requester_id:
        q += " AND po.requester_id = ?"; params.append(requester_id)
    if vendor_id:
        q += " AND po.vendor_id = ?"; params.append(vendor_id)
    q += " ORDER BY po.requested_at DESC LIMIT ?"; params.append(limit)
    with cursor() as conn:
        return [dict(r) for r in conn.execute(q, params).fetchall()]


def pending_count():
    with cursor() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM purchase_orders WHERE status = 'PENDING'"
        ).fetchone()[0]
