"""⑤ 발주 요청 (계획서 7.2).

거래처 선택 → 품목 담기(장바구니) → 현재고·안전재고 참고 → 임시저장/결재요청.
"""
import streamlit as st

from screens._shared import require, clear_cache, fmt_won, fmt_qty
from db.queries import list_vendors, list_items, get_item
from core import inventory, purchase


def render():
    user = require()
    st.title("🛒 발주 요청")

    if "cart" not in st.session_state:
        st.session_state.cart = {}  # item_id -> {qty, unit_price}

    vendors = list_vendors()
    if not vendors:
        st.info("먼저 ‘거래처·품목 관리’에서 거래처를 등록하세요.")
        return

    vmap = {v["name"]: v["id"] for v in vendors}
    vname = st.selectbox("거래처", list(vmap.keys()))
    vendor_id = vmap[vname]

    items = list_items(vendor_id=vendor_id)
    if not items:
        items = list_items()  # 기본거래처 미지정 품목도 담을 수 있게
        st.caption("이 거래처 전용 품목이 없어 전체 품목을 표시합니다.")

    st.subheader("품목 담기")
    for it in items:
        stock = inventory.current_stock(it["id"])
        low = stock < (it["safety_stock"] or 0)
        cols = st.columns([3, 2, 2, 2, 1.5])
        with cols[0]:
            flag = "🔴" if low else ""
            st.markdown(f"**{it['name']}** {it['spec'] or ''} {flag}")
            st.caption(f"현재고 {fmt_qty(stock)}{it['unit']} · "
                       f"안전 {fmt_qty(it['safety_stock'])}{it['unit']}")
        with cols[1]:
            qty = st.number_input("수량", min_value=0.0, step=1.0, key=f"q_{it['id']}",
                                  label_visibility="collapsed")
        with cols[2]:
            price = st.number_input("단가", min_value=0, step=100,
                                    value=int(it["unit_price"] or 0),
                                    key=f"p_{it['id']}", label_visibility="collapsed")
        with cols[3]:
            st.markdown(f"금액: **{fmt_won(int(qty * price))}**")
        with cols[4]:
            if st.button("담기", key=f"add_{it['id']}"):
                if qty > 0:
                    st.session_state.cart[it["id"]] = {
                        "qty": qty, "unit_price": int(price)}
                    st.rerun()
                else:
                    st.warning("수량을 입력하세요.")

    st.divider()
    st.subheader("🧺 장바구니")
    cart = st.session_state.cart
    if not cart:
        st.caption("담긴 품목이 없습니다.")
        return

    total = 0
    for item_id, ln in list(cart.items()):
        it = get_item(item_id)
        amt = int(ln["qty"] * ln["unit_price"])
        total += amt
        cols = st.columns([4, 2, 2, 2, 1])
        cols[0].markdown(f"**{it['name']}** {it['spec'] or ''}")
        cols[1].markdown(f"{fmt_qty(ln['qty'])}{it['unit']}")
        cols[2].markdown(fmt_won(ln["unit_price"]))
        cols[3].markdown(f"**{fmt_won(amt)}**")
        if cols[4].button("✕", key=f"del_{item_id}"):
            del cart[item_id]
            st.rerun()

    st.markdown(f"### 합계: {fmt_won(total)}")
    memo = st.text_input("메모(선택)")

    c1, c2 = st.columns(2)
    lines = [{"item_id": iid, "qty": ln["qty"], "unit_price": ln["unit_price"]}
             for iid, ln in cart.items()]
    with c1:
        if st.button("💾 임시저장", use_container_width=True):
            po_id = purchase.create_po(vendor_id, user["id"], lines, memo, submit=False)
            st.session_state.cart = {}
            clear_cache()
            st.success(f"임시저장 완료 (발주 #{po_id}). ‘발주 현황’에서 이어서 요청하세요.")
    with c2:
        if st.button("📤 결재 요청", type="primary", use_container_width=True):
            po_id = purchase.create_po(vendor_id, user["id"], lines, memo, submit=True)
            st.session_state.cart = {}
            clear_cache()
            st.success(f"결재 요청 완료 (발주 #{po_id}). 결재자 승인을 기다립니다.")
