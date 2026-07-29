"""② 대시보드 (계획서 7.2)."""
import streamlit as st

from screens._shared import require, fmt_won, fmt_qty
from core import purchase, invoice, inventory, payment, report


def render():
    user = require()
    st.title("📊 대시보드")

    approver = user["role"] in ("APPROVER", "ADMIN")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("승인 대기 발주", f"{purchase.pending_count()}건")
    with c2:
        st.metric("검수 대기 명세서", f"{invoice.pending_review_count()}건")
    with c3:
        st.metric("이번 달 지출", fmt_won(report.spend_this_month()))
    with c4:
        st.metric("미결제 총액", fmt_won(payment.total_outstanding()))

    if approver and purchase.pending_count() > 0:
        st.warning(f"⏳ 승인 대기 발주가 {purchase.pending_count()}건 있습니다. "
                   "‘승인함’에서 확인하세요.")

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("⚠️ 안전재고 미달")
        low = inventory.low_stock_items()
        if not low:
            st.success("미달 품목이 없습니다.")
        else:
            for r in low:
                st.markdown(
                    f"- **{r['name']}** {r['spec'] or ''} — 현재 "
                    f"{fmt_qty(r['stock'])}{r['unit']} / 안전 "
                    f"{fmt_qty(r['safety_stock'])}{r['unit']} "
                    f"(부족 {fmt_qty(r['shortage'])})")

    with right:
        st.subheader(f"⏰ 유통기한 임박")
        exp = inventory.expiring_lots()
        if not exp:
            st.success("임박 품목이 없습니다.")
        else:
            for r in exp:
                tag = "🔴 만료" if r["days_left"] < 0 else f"D-{r['days_left']}"
                st.markdown(
                    f"- **{r['name']}** (로트 {r['lot_no'] or '-'}) "
                    f"{r['expiry_date']} · {tag}")

    st.divider()
    st.subheader("🕑 최근 활동")
    acts = report.recent_activity(10)
    if not acts:
        st.caption("활동 내역이 없습니다.")
    else:
        action_kr = {"REQUEST": "발주요청", "RESUBMIT": "재요청", "DRAFT": "임시저장",
                     "APPROVE": "승인", "REJECT": "반려", "CANCEL": "취소",
                     "CONFIRM": "명세서확정"}
        for a in acts:
            doc = "발주" if a["doc_type"] == "PO" else "명세서"
            st.markdown(
                f"- `{a['ts'][:16].replace('T',' ')}` **{a['user_name']}** — "
                f"{doc} #{a['doc_id']} {action_kr.get(a['action'], a['action'])}")
