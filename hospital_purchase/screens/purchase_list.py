"""⑦ 발주 현황 (계획서 7.2). 상태별 탭, PDF 출력, 취소, 재요청."""
import streamlit as st

from screens._shared import require, clear_cache, fmt_won, fmt_qty
from core import purchase
from db.queries import get_logs

STATUS_KR = {
    "DRAFT": "임시저장", "PENDING": "승인대기", "APPROVED": "승인",
    "REJECTED": "반려", "RECEIVING": "부분입고", "CLOSED": "입고완료",
    "CANCELED": "취소",
}
TABS = ["전체", "DRAFT", "PENDING", "APPROVED", "RECEIVING", "CLOSED",
        "REJECTED", "CANCELED"]


def render():
    user = require()
    st.title("📋 발주 현황")

    tabs = st.tabs([STATUS_KR.get(t, t) for t in TABS])
    for tab, status in zip(tabs, TABS):
        with tab:
            pos = purchase.list_pos(status=None if status == "전체" else status)
            if not pos:
                st.caption("해당 상태의 발주가 없습니다.")
                continue
            for po in pos:
                _po_row(po, user, scope=status)


def _po_row(po, user, scope=""):
    k = f"{scope}_{po['id']}"
    label = (f"#{po['po_number']} · {po['vendor_name']} · "
             f"{fmt_won(po['total_amount'])} · {STATUS_KR.get(po['status'])} · "
             f"{po['requester_name']}")
    with st.expander(label):
        items = purchase.get_po_items(po["id"])
        for it in items:
            recv = f" (입고 {fmt_qty(it['received_qty'])}/{fmt_qty(it['qty'])})" \
                if it["received_qty"] else ""
            st.markdown(f"- {it['item_name']} {it['spec'] or ''} · "
                        f"{fmt_qty(it['qty'])}{it['unit']} × {fmt_won(it['unit_price'])}"
                        f"{recv}")
        logs = get_logs("PO", po["id"])
        if logs:
            st.caption(" · ".join(
                f"{lg['action']} {lg['user_name']} {lg['acted_at'][:16].replace('T',' ')}"
                for lg in logs))

        c1, c2, c3 = st.columns(3)
        # 재요청 (반려 → 결재요청)
        if po["status"] in ("DRAFT", "REJECTED"):
            with c1:
                if st.button("📤 결재 요청", key=f"sub_{k}"):
                    try:
                        purchase.submit(po["id"], user["id"])
                        clear_cache(); st.success("결재 요청됨."); st.rerun()
                    except Exception as e:
                        st.error(str(e))
        # 취소
        if po["status"] in ("DRAFT", "PENDING", "APPROVED", "RECEIVING"):
            with c2:
                if st.button("🚫 취소", key=f"cxl_{k}"):
                    try:
                        purchase.cancel(po["id"], user["id"])
                        clear_cache(); st.warning("취소됨."); st.rerun()
                    except Exception as e:
                        st.error(str(e))
        # PDF
        with c3:
            if st.button("📄 발주서 PDF", key=f"pdf_{k}"):
                _make_pdf(po, items, logs, k)


def _make_pdf(po, items, logs, k):
    try:
        from utils.pdf import po_pdf
        data = po_pdf(po, items, logs)
        st.download_button("⬇️ 다운로드", data,
                           file_name=f"{po['po_number']}.pdf",
                           mime="application/pdf", key=f"dl_{k}")
    except Exception as e:
        st.error(f"PDF 생성 실패(reportlab 필요): {e}")
