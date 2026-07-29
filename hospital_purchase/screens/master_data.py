"""③④ 거래처·품목 관리 — 결재자 전용 (계획서 7.2)."""
import streamlit as st

from screens._shared import require, clear_cache, fmt_won
from db.queries import (
    create_vendor, update_vendor, list_vendors, get_vendor,
    create_item, update_item, list_items, get_vendor as _gv, CATEGORIES,
)
from core import inventory
from core.auth import POSITIONS  # noqa
from db.queries import get_vendor  # noqa


def render():
    require("APPROVER")
    st.title("🗂️ 거래처·품목 관리")
    tab_v, tab_i = st.tabs(["거래처", "품목"])
    with tab_v:
        _vendors()
    with tab_i:
        _items()


def _vendors():
    st.subheader("거래처 등록")
    with st.form("new_vendor", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("거래처명 *")
        business_no = c2.text_input("사업자등록번호")
        contact = c1.text_input("담당자")
        phone = c2.text_input("연락처")
        email = c1.text_input("이메일")
        terms = c2.text_input("결제조건 * (예: 말일결산 익월10일)")
        memo = st.text_area("메모 (OCR 프롬프트는 'PROMPT:' 뒤에 작성)")
        if st.form_submit_button("등록", type="primary"):
            if not name or not terms:
                st.error("거래처명과 결제조건은 필수입니다.")
            else:
                create_vendor(name, business_no, contact, phone, email, terms, memo)
                clear_cache(); st.success("거래처 등록 완료."); st.rerun()

    st.divider()
    st.subheader("거래처 목록")
    for v in list_vendors(active_only=False):
        tag = "" if v["is_active"] else " · ⛔비활성"
        with st.expander(f"{v['name']}{tag} · {v.get('payment_terms') or ''}"):
            c1, c2 = st.columns(2)
            name = c1.text_input("거래처명", value=v["name"], key=f"vn_{v['id']}")
            terms = c2.text_input("결제조건", value=v.get("payment_terms") or "",
                                  key=f"vt_{v['id']}")
            phone = c1.text_input("연락처", value=v.get("phone") or "",
                                  key=f"vp_{v['id']}")
            memo = c2.text_input("메모", value=v.get("memo") or "", key=f"vm_{v['id']}")
            b1, b2 = st.columns(2)
            if b1.button("수정 저장", key=f"vs_{v['id']}"):
                update_vendor(v["id"], name=name, payment_terms=terms, phone=phone,
                              memo=memo)
                clear_cache(); st.success("저장됨."); st.rerun()
            if b2.button("비활성화" if v["is_active"] else "활성화",
                         key=f"va_{v['id']}"):
                update_vendor(v["id"], is_active=0 if v["is_active"] else 1)
                clear_cache(); st.rerun()


def _items():
    vendors = list_vendors()
    vmap = {"(기본거래처 없음)": None}
    vmap.update({v["name"]: v["id"] for v in vendors})

    st.subheader("품목 등록")
    with st.form("new_item", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("품목명 *")
        spec = c2.text_input("규격 (500ml, 100T 등)")
        unit = c3.text_input("단위 * (박스/개/병/EA)", value="EA")
        cat = c1.selectbox("분류 *", CATEGORIES)
        vname = c2.selectbox("기본 거래처", list(vmap.keys()))
        price = c3.number_input("단가(원)", min_value=0, step=100)
        safety = c1.number_input("안전재고", min_value=0.0, step=1.0)
        if st.form_submit_button("등록", type="primary"):
            if not name or not unit:
                st.error("품목명과 단위는 필수입니다.")
            else:
                create_item(name, unit, cat, spec=spec,
                            default_vendor_id=vmap[vname], unit_price=price,
                            safety_stock=safety)
                clear_cache(); st.success("품목 등록 완료."); st.rerun()

    with st.expander("📥 엑셀 일괄 업로드"):
        try:
            from utils.excel import items_template_xlsx, parse_items_upload
            st.download_button("템플릿 다운로드", items_template_xlsx(),
                               file_name="품목_템플릿.xlsx",
                               mime="application/vnd.openxmlformats-officedocument."
                                    "spreadsheetml.sheet")
            up = st.file_uploader("작성한 엑셀 업로드", type=["xlsx"])
            default_vendor = st.selectbox("기본 거래처(선택)", list(vmap.keys()),
                                          key="bulk_v")
            if up and st.button("업로드 반영"):
                rows = parse_items_upload(up)
                for r in rows:
                    create_item(r["name"], r["unit"], r["category"], spec=r["spec"],
                                default_vendor_id=vmap[default_vendor],
                                unit_price=r["unit_price"], safety_stock=r["safety_stock"])
                clear_cache(); st.success(f"{len(rows)}개 품목 등록됨."); st.rerun()
        except Exception as e:
            st.caption(f"엑셀 기능 사용 불가: {e}")

    st.divider()
    st.subheader("품목 목록")
    cat_filter = st.selectbox("분류 필터", ["전체"] + list(CATEGORIES))
    search = st.text_input("검색", key="item_search")
    items = list_items(active_only=False,
                       category=None if cat_filter == "전체" else cat_filter,
                       search=search or None)
    for it in items:
        stock = inventory.current_stock(it["id"])
        tag = "" if it["is_active"] else " · ⛔비활성"
        with st.expander(f"[{it['category']}] {it['name']} {it['spec'] or ''}{tag} "
                         f"· 현재고 {stock:g}{it['unit']}"):
            c1, c2, c3 = st.columns(3)
            price = c1.number_input("단가", min_value=0, value=int(it["unit_price"] or 0),
                                    step=100, key=f"ip_{it['id']}")
            safety = c2.number_input("안전재고", min_value=0.0,
                                     value=float(it["safety_stock"] or 0), step=1.0,
                                     key=f"is_{it['id']}")
            unit = c3.text_input("단위", value=it["unit"], key=f"iu_{it['id']}")
            b1, b2 = st.columns(2)
            if b1.button("수정 저장", key=f"isave_{it['id']}"):
                update_item(it["id"], unit_price=price, safety_stock=safety, unit=unit)
                clear_cache(); st.success("저장됨."); st.rerun()
            if b2.button("비활성화" if it["is_active"] else "활성화",
                         key=f"ia_{it['id']}"):
                update_item(it["id"], is_active=0 if it["is_active"] else 1)
                clear_cache(); st.rerun()
