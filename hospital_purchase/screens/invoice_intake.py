"""⑧ 명세서 입고 (계획서 6장 파이프라인 + 검수 화면).

업로드 → 품질검사 → 보정 → OCR → 매칭 → 검수(좌: 이미지 / 우: 표) → 확정.
OCR/보정을 못 쓰는 환경에서도 수동 입력으로 입고할 수 있다.
"""
import json

import streamlit as st

from screens._shared import require, clear_cache, fmt_won, fmt_qty
from db.queries import list_vendors, list_items, get_item
from core import purchase, invoice, matching
from ocr import pipeline


def render():
    user = require()
    st.title("🧾 명세서 입고")

    tab_new, tab_review = st.tabs(["새 명세서 업로드", "검수 대기 목록"])
    with tab_new:
        _upload_flow(user)
    with tab_review:
        _review_list(user)


def _upload_flow(user):
    vendors = list_vendors()
    if not vendors:
        st.info("먼저 거래처를 등록하세요.")
        return
    vmap = {v["name"]: v for v in vendors}
    vname = st.selectbox("거래처", list(vmap.keys()), key="inv_vendor")
    vendor = vmap[vname]

    # R2: 승인/부분입고 발주만 연결 가능
    recv_pos = purchase.list_pos(status=list(purchase.RECEIVABLE_STATES),
                                 vendor_id=vendor["id"])
    po_opts = {"(연결 안 함 · 직접구매)": None}
    for po in recv_pos:
        po_opts[f"{po['po_number']} ({fmt_won(po['total_amount'])})"] = po["id"]
    po_label = st.selectbox("연결 발주 (승인된 발주만 표시 · R2)", list(po_opts.keys()))
    po_id = po_opts[po_label]

    up = st.file_uploader("명세서 사진 업로드", type=["jpg", "jpeg", "png"])
    if up and st.button("⚙️ 자동 처리 시작", type="primary"):
        with st.spinner("저장·품질검사·보정·OCR 진행 중..."):
            path = pipeline.save_upload(up.getvalue(), vendor["name"], up.name)
            result = pipeline.process(path, vendor)
        st.session_state.intake = {
            "vendor_id": vendor["id"], "po_id": po_id,
            "original": str(path), "result": result}
        st.rerun()

    intake = st.session_state.get("intake")
    if intake and intake["vendor_id"] == vendor["id"]:
        _draft_editor(user, vendor, po_id, intake)


def _draft_editor(user, vendor, po_id, intake):
    result = intake["result"]
    q = result["quality"]

    st.divider()
    # 품질 게이트 표시
    if q["warnings"]:
        for w in q["warnings"]:
            st.warning(w)
    if not q["ok"]:
        st.error("해상도 미달로 차단되었습니다. 재촬영 후 다시 업로드하세요.")
    if result["ocr_error"]:
        st.info(f"OCR 참고: {result['ocr_error']} — 아래 표에 직접 입력할 수 있습니다.")

    col_img, col_tbl = st.columns([1, 1.4])
    with col_img:
        st.subheader("명세서 이미지")
        show = result["processed_path"] or intake["original"]
        try:
            st.image(show, use_container_width=True)
        except Exception:
            st.caption(show)

    with col_tbl:
        st.subheader("파싱 결과 (수정 가능)")
        header = result["header"]
        invoice_no = st.text_input("명세서 번호", value=header.get("invoice_no") or "")
        issue_date = st.text_input("발행일 (YYYY-MM-DD)",
                                   value=header.get("issue_date") or "")

        all_items = list_items()
        item_label = {i["id"]: f"{i['name']} {i['spec'] or ''}".strip()
                      for i in all_items}
        label_to_id = {v: k for k, v in item_label.items()}
        choices = ["(미매칭)"] + list(label_to_id.keys())

        edited = []
        rows = result["items"] or [{
            "ocr_item_name": "", "item_id": None, "qty": 0.0, "unit_price": 0,
            "amount": 0, "lot_no": None, "expiry_date": None,
            "match_status": "UNMATCHED"}]
        for idx, row in enumerate(rows):
            st.markdown(f"**행 {idx + 1}** · 매칭: `{row['match_status']}`")
            cur_label = item_label.get(row["item_id"], "(미매칭)")
            if cur_label not in choices:
                cur_label = "(미매칭)"
            cc = st.columns([3, 2, 2, 2])
            ocr_name = cc[0].text_input("OCR 품목명", value=row["ocr_item_name"],
                                        key=f"on_{idx}")
            picked = cc[0].selectbox("매칭 품목", choices,
                                     index=choices.index(cur_label), key=f"mi_{idx}")
            qty = cc[1].number_input("수량", min_value=0.0, step=1.0,
                                     value=float(row["qty"]), key=f"qt_{idx}")
            price = cc[2].number_input("단가", min_value=0, step=100,
                                       value=int(row["unit_price"]), key=f"pr_{idx}")
            lot = cc[3].text_input("로트", value=row.get("lot_no") or "", key=f"lt_{idx}")
            exp = cc[3].text_input("유통기한", value=row.get("expiry_date") or "",
                                   key=f"ex_{idx}")
            item_id = label_to_id.get(picked)
            edited.append({
                "ocr_item_name": ocr_name, "item_id": item_id, "qty": qty,
                "unit_price": int(price), "amount": int(qty * price),
                "lot_no": lot or None, "expiry_date": exp or None,
                "match_status": "MATCHED" if item_id else "UNMATCHED"})
            st.divider()

        total = sum(r["amount"] for r in edited)
        st.markdown(f"### 합계: {fmt_won(total)}")

        if st.button("💾 검수 대기로 저장", use_container_width=True):
            try:
                inv_id = invoice.create_invoice(
                    vendor["id"], intake["original"], user["id"],
                    invoice_no=invoice_no or None, issue_date=issue_date or None,
                    po_id=po_id, processed_file=result["processed_path"],
                    ocr_raw=json.dumps(result["ocr"], ensure_ascii=False)
                    if result["ocr"] else None,
                    total_amount=total, ocr_items=edited)
                st.session_state.pop("intake", None)
                clear_cache()
                st.success(f"명세서 #{inv_id} 저장됨. ‘검수 대기 목록’에서 확정하세요.")
                st.rerun()
            except Exception as e:
                st.error(str(e))


def _review_list(user):
    pending = invoice.list_invoices(status="PENDING_REVIEW")
    if not pending:
        st.caption("검수 대기 명세서가 없습니다.")
        return
    for inv in pending:
        with st.expander(f"#{inv['id']} · {inv['vendor_name']} · "
                         f"{inv.get('invoice_no') or '번호미상'} · "
                         f"{fmt_won(inv['total_amount'])}"):
            _review_one(user, inv["id"])


def _review_one(user, inv_id):
    inv = invoice.get_invoice(inv_id)
    tw = invoice.three_way(inv_id)
    st.markdown(f"연결 발주: **{inv.get('po_number') or '없음(직접구매)'}**")

    for ln in tw["lines"]:
        name = ln.get("item_name") or ln["ocr_item_name"]
        st.markdown(
            f"{ln['signal']} **{name}** · {fmt_qty(ln['qty'])} × "
            f"{fmt_won(ln['unit_price'])} = {fmt_won(ln['amount'])}"
            + (f" · {ln['note']}" if ln["note"] else ""))

    if tw["blockers"]:
        st.error("확정 차단: " + " / ".join(tw["blockers"]))

    update_prices = st.checkbox("단가 변경분을 품목 마스터에 반영",
                                key=f"up_{inv_id}")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ 확정 (재고 반영)", key=f"cf_{inv_id}", type="primary",
                     disabled=not tw["can_confirm"], use_container_width=True):
            try:
                invoice.confirm(inv_id, user["id"], update_prices=update_prices)
                clear_cache(); st.success("확정 완료. 재고에 반영되었습니다."); st.rerun()
            except Exception as e:
                st.error(str(e))
    with c2:
        reason = st.text_input("반려 사유", key=f"irr_{inv_id}")
        if st.button("✗ 반려", key=f"irj_{inv_id}", use_container_width=True):
            try:
                invoice.reject(inv_id, user["id"], reason)
                clear_cache(); st.warning("반려됨."); st.rerun()
            except Exception as e:
                st.error(str(e))
