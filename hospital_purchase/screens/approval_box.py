"""⑥ 승인함 — 결재자 전용 (계획서 7.2). R4/R5 적용."""
import streamlit as st

from screens._shared import require, clear_cache, fmt_won, fmt_qty
from core import purchase, inventory


def render():
    user = require("APPROVER")
    st.title("✅ 승인함")

    pending = purchase.list_pos(status="PENDING")
    if not pending:
        st.success("승인 대기 중인 발주가 없습니다.")
        return

    st.caption(f"승인 대기 {len(pending)}건")

    for po in pending:
        with st.expander(
                f"#{po['po_number']} · {po['vendor_name']} · "
                f"{fmt_won(po['total_amount'])} · 요청 {po['requester_name']}"):
            items = purchase.get_po_items(po["id"])
            for it in items:
                stock = inventory.current_stock(it["item_id"])
                st.markdown(
                    f"- **{it['item_name']}** {it['spec'] or ''} · "
                    f"{fmt_qty(it['qty'])}{it['unit']} × {fmt_won(it['unit_price'])} "
                    f"= {fmt_won(it['amount'])}  \n"
                    f"  <span style='color:gray'>현재고 {fmt_qty(stock)}{it['unit']}</span>",
                    unsafe_allow_html=True)
            if po["memo"]:
                st.caption(f"메모: {po['memo']}")

            self_req = po["requester_id"] == user["id"]
            if self_req:
                st.info("본인이 요청한 발주입니다. (R4: 원장 셀프승인 설정에 따름)")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("✓ 승인", key=f"ap_{po['id']}", type="primary",
                             use_container_width=True):
                    try:
                        purchase.approve(user, po["id"])
                        clear_cache()
                        st.success("승인 완료.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with c2:
                reason = st.text_input("반려 사유", key=f"rr_{po['id']}")
                if st.button("✗ 반려", key=f"rj_{po['id']}",
                             use_container_width=True):
                    try:
                        purchase.reject(user, po["id"], reason)
                        clear_cache()
                        st.warning("반려 처리됨.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
