"""⑫ 거래처별 현황 — 결재자 전용 (계획서 7.2).

카드 뷰 + 월별 매트릭스 + 거래처 상세(단가 추이, 명세서) + 엑셀 내보내기.
"""
import streamlit as st
import pandas as pd

from screens._shared import require, fmt_won
from core import report, invoice
from db.queries import list_vendors, list_items


def render():
    require("APPROVER")
    st.title("🏢 거래처별 현황")

    tab_card, tab_matrix, tab_detail = st.tabs(["카드 뷰", "월별 매트릭스", "거래처 상세"])

    with tab_card:
        cards = report.vendor_cards()
        if not cards:
            st.caption("데이터가 없습니다.")
        cols = st.columns(3)
        for i, c in enumerate(cards):
            with cols[i % 3]:
                st.markdown(f"#### {c['vendor_name']}")
                st.markdown(f"- 이번 달 입고: {c['month_count']}건 / "
                            f"{fmt_won(c['month_amount'])}")
                st.markdown(f"- 미결제: **{fmt_won(c['outstanding'])}**")
                st.markdown(f"- 최근 거래일: {c['last_date']}")
                st.divider()

    with tab_matrix:
        m = report.vendor_monthly_matrix()
        if not m["rows"]:
            st.caption("확정된 명세서가 없습니다.")
        else:
            records = []
            for row in m["rows"]:
                rec = {"거래처": row["vendor_name"]}
                for month in m["months"]:
                    rec[month] = row["cells"].get(month, 0)
                rec["합계"] = row["total"]
                records.append(rec)
            st.dataframe(pd.DataFrame(records), use_container_width=True,
                         hide_index=True)
        try:
            from utils.excel import vendor_monthly_xlsx
            st.download_button("⬇️ 월별 정산표(엑셀)", vendor_monthly_xlsx(),
                               file_name="거래처_월별정산.xlsx",
                               mime="application/vnd.openxmlformats-officedocument."
                                    "spreadsheetml.sheet")
        except Exception as e:
            st.caption(f"엑셀 내보내기 불가: {e}")

    with tab_detail:
        vendors = list_vendors()
        vmap = {v["name"]: v["id"] for v in vendors}
        if not vmap:
            return
        vname = st.selectbox("거래처", list(vmap.keys()))
        vid = vmap[vname]

        st.markdown("**명세서 이력**")
        for inv in invoice.list_invoices(vendor_id=vid):
            st.markdown(f"- #{inv['id']} · {inv.get('invoice_no') or '-'} · "
                        f"{inv.get('issue_date') or '-'} · {inv['status']} · "
                        f"{fmt_won(inv['total_amount'])}")

        st.markdown("**품목별 단가 추이**")
        items = list_items(vendor_id=vid)
        if items:
            imap = {f"{i['name']} {i['spec'] or ''}".strip(): i["id"] for i in items}
            pick = st.selectbox("품목", list(imap.keys()))
            hist = report.price_history(imap[pick])
            if hist:
                df = pd.DataFrame(hist).set_index("date")["unit_price"]
                st.line_chart(df)
            else:
                st.caption("확정된 단가 이력이 없습니다.")

        try:
            from utils.excel import vendor_detail_xlsx
            st.download_button("⬇️ 이 거래처 정산(엑셀)", vendor_detail_xlsx(vid),
                               file_name=f"{vname}_정산.xlsx",
                               mime="application/vnd.openxmlformats-officedocument."
                                    "spreadsheetml.sheet")
        except Exception:
            pass
