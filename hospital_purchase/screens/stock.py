"""⑩ 재고 현황 (계획서 7.2). 현재고/안전재고/부족, 이력 타임라인, 월별 사용량."""
import streamlit as st
import pandas as pd

from screens._shared import require, fmt_qty, fmt_won
from core import inventory, report
from db.queries import get_item


def render():
    require()
    st.title("📦 재고 현황")

    rows = inventory.stock_overview()
    if not rows:
        st.info("등록된 품목이 없습니다.")
        return

    cats = ["전체"] + sorted({r["category"] for r in rows})
    c1, c2 = st.columns([1, 2])
    cat = c1.selectbox("분류", cats)
    kw = c2.text_input("검색")
    filtered = [r for r in rows
                if (cat == "전체" or r["category"] == cat)
                and (not kw or kw.lower() in r["name"].lower())]

    only_low = st.checkbox("안전재고 미달만 보기")
    if only_low:
        filtered = [r for r in filtered if r["below_safety"]]

    # 엑셀 내보내기
    try:
        from utils.excel import stock_xlsx
        st.download_button("⬇️ 재고 엑셀", stock_xlsx(),
                           file_name="재고현황.xlsx",
                           mime="application/vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet")
    except Exception:
        pass

    df = pd.DataFrame([{
        "분류": r["category"], "품목": r["name"], "규격": r["spec"] or "",
        "단위": r["unit"], "현재고": r["stock"], "안전재고": r["safety_stock"],
        "부족분": r["shortage"] if r["below_safety"] else 0,
        "상태": "🔴 미달" if r["below_safety"] else "🟢",
    } for r in filtered])
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("품목 상세 · 입출고 이력")
    label = {f"{r['name']} {r['spec'] or ''}".strip(): r["id"] for r in filtered}
    if not label:
        return
    picked = st.selectbox("품목 선택", list(label.keys()))
    item_id = label[picked]
    item = get_item(item_id)

    colL, colR = st.columns(2)
    with colL:
        st.markdown("**입출고 타임라인**")
        moves = inventory.movements_for(item_id)
        type_kr = {"IN": "입고", "USE": "사용", "DISPOSE": "폐기", "ADJUST": "조정"}
        if not moves:
            st.caption("이력이 없습니다.")
        for m in moves:
            sign = "＋" if m["qty"] > 0 else "－"
            st.markdown(
                f"- `{m['moved_at'][:16].replace('T',' ')}` "
                f"{type_kr.get(m['move_type'])} {sign}{fmt_qty(abs(m['qty']))}"
                f"{item['unit']} · {m['user_name']}"
                + (f" · {m['reason']}" if m['reason'] else ""))
    with colR:
        st.markdown("**월별 사용량**")
        usage = report.monthly_usage(item_id)
        if usage:
            st.bar_chart(pd.DataFrame({"사용량": usage}))
        else:
            st.caption("사용 이력이 없습니다.")

        if inventory.current_stock(item_id) < (item["safety_stock"] or 0):
            st.error("안전재고 미달 — ‘발주 요청’에서 보충 발주를 진행하세요.")
