"""⑪ 결제 관리 — 결재자 전용 (계획서 7.2). R9 미결제 추적, 일괄 결제."""
import streamlit as st

from screens._shared import require, clear_cache, fmt_won
from core import payment
from db.queries import list_vendors


def render():
    user = require("APPROVER")
    st.title("💳 결제 관리")
    st.caption("‘결제(대금 지급)’ 화면입니다. 발주 승인(결재)과는 별개입니다.")

    st.subheader("거래처별 미결제 잔액")
    summary = payment.outstanding_by_vendor()
    if not summary:
        st.success("미결제 잔액이 없습니다.")
    else:
        for s in summary:
            overdue = f" · 최장 연체 {s['max_overdue']}일" if s["max_overdue"] else ""
            st.markdown(f"- **{s['vendor_name']}** · {fmt_won(s['balance'])} "
                        f"({s['count']}건){overdue}")
        st.markdown(f"### 총 미결제: {fmt_won(payment.total_outstanding())}")

    st.divider()
    st.subheader("일괄 결제 처리")
    vendors = list_vendors()
    vmap = {v["name"]: v["id"] for v in vendors}
    if not vmap:
        return
    vname = st.selectbox("거래처", list(vmap.keys()))
    vendor_id = vmap[vname]

    unpaid = payment.unpaid_invoices(vendor_id)
    if not unpaid:
        st.caption("이 거래처는 미결제 명세서가 없습니다.")
    else:
        allocations = []
        for inv in unpaid:
            cols = st.columns([3, 2, 2, 2])
            checked = cols[0].checkbox(
                f"#{inv['id']} {inv.get('invoice_no') or ''} "
                f"({inv.get('issue_date') or '-'})", key=f"chk_{inv['id']}")
            cols[1].markdown(f"잔액 {fmt_won(inv['balance'])}")
            if inv["overdue_days"]:
                cols[2].markdown(f"🔴 {inv['overdue_days']}일 연체")
            amt = cols[3].number_input("지급액", min_value=0, max_value=inv["balance"],
                                       value=inv["balance"] if checked else 0,
                                       step=1000, key=f"amt_{inv['id']}",
                                       label_visibility="collapsed")
            if checked and amt > 0:
                allocations.append({"invoice_id": inv["id"], "applied_amount": amt})

        method = st.selectbox("결제 방법", payment.METHODS)
        memo = st.text_input("메모(선택)")
        total = sum(a["applied_amount"] for a in allocations)
        st.markdown(f"**결제 예정액: {fmt_won(total)}**")
        if st.button("💳 결제 실행", type="primary", disabled=not allocations):
            try:
                payment.pay(vendor_id, allocations, user["id"], method=method,
                            memo=memo)
                clear_cache(); st.success("결제 완료."); st.rerun()
            except Exception as e:
                st.error(str(e))

    st.divider()
    st.subheader("결제 이력")
    for p in payment.list_payments(vendor_id=vendor_id):
        st.markdown(f"- `{p['paid_at'][:16].replace('T',' ')}` "
                    f"{fmt_won(p['amount'])} · {p['method']} · {p['handler_name']}"
                    + (f" · {p['memo']}" if p['memo'] else ""))
