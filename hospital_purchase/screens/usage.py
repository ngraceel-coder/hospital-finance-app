"""⑨ 사용 등록 (계획서 7.2). 사용/폐기/실사 조정(사유 필수)."""
import streamlit as st

from screens._shared import require, clear_cache, fmt_qty
from db.queries import list_items, get_item
from core import inventory


def render():
    user = require()
    st.title("✏️ 사용 등록")

    items = list_items()
    if not items:
        st.info("등록된 품목이 없습니다.")
        return
    label = {f"{i['name']} {i['spec'] or ''}".strip(): i["id"] for i in items}
    search = st.text_input("품목 검색")
    keys = [k for k in label if search.lower() in k.lower()] if search else list(label)
    if not keys:
        st.caption("검색 결과가 없습니다.")
        return
    picked = st.selectbox("품목", keys)
    item = get_item(label[picked])
    stock = inventory.current_stock(item["id"])
    st.metric(f"{item['name']} 현재고", f"{fmt_qty(stock)}{item['unit']}")

    mode = st.radio("유형", ["사용", "폐기", "실사 조정"], horizontal=True)

    if mode == "사용":
        qty = st.number_input("사용 수량", min_value=0.0, step=1.0)
        reason = st.text_input("메모(선택)")
        if st.button("차감 기록", type="primary"):
            if qty <= 0:
                st.warning("수량을 입력하세요.")
            else:
                inventory.use_item(item["id"], qty, user["id"], reason=reason)
                clear_cache(); st.success("사용 기록 완료."); st.rerun()

    elif mode == "폐기":
        qty = st.number_input("폐기 수량", min_value=0.0, step=1.0)
        reason = st.text_input("폐기 사유 (필수)")
        if st.button("폐기 기록", type="primary"):
            try:
                if qty <= 0:
                    raise ValueError("수량을 입력하세요.")
                inventory.dispose_item(item["id"], qty, user["id"], reason)
                clear_cache(); st.success("폐기 기록 완료."); st.rerun()
            except Exception as e:
                st.error(str(e))

    else:  # 실사 조정
        target = st.number_input("실제 재고(실사값)", min_value=0.0, step=1.0,
                                 value=float(stock))
        reason = st.text_input("조정 사유 (필수)")
        st.caption(f"조정량: {fmt_qty(target - stock)}{item['unit']}")
        if st.button("실사 반영", type="primary"):
            try:
                inventory.adjust_stock(item["id"], target, user["id"], reason)
                clear_cache(); st.success("실사 조정 완료."); st.rerun()
            except Exception as e:
                st.error(str(e))
