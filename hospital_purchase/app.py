"""병원 구매·재고 관리 앱 — 진입점 / 라우팅 / 세션.

실행:
  cd hospital_purchase
  pip install -r requirements.txt
  streamlit run app.py
  (내부망 공유) streamlit run app.py --server.address 0.0.0.0
"""
import streamlit as st

from config import ORG_NAME, ORG_UNIT
from db.init_db import ensure_db
from utils.backup import auto_backup
from core.auth import authenticate

st.set_page_config(page_title=f"{ORG_NAME} 구매·재고", page_icon="🏥", layout="wide")

# 앱 시작 시 1회: 스키마 보장 + 백업
if "booted" not in st.session_state:
    ensure_db()
    auto_backup()
    st.session_state.booted = True


def login_view():
    st.title("🏥 병원 구매·재고 관리")
    st.caption(f"{ORG_NAME} · {ORG_UNIT}")
    with st.form("login"):
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인", use_container_width=True)
    if submitted:
        user = authenticate(username, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("아이디 또는 비밀번호가 올바르지 않습니다. (비활성 계정 불가)")
    st.info("초기 관리자 계정: **admin / admin1234** (로그인 후 비밀번호를 변경하세요)")


def build_nav(user):
    """역할별 메뉴 노출 (계획서 7.1)."""
    from screens import (
        dashboard, purchase_request, approval_box, purchase_list,
        invoice_intake, usage, stock, payment, vendor_status,
        master_data, user_admin,
    )

    role = user["role"]
    approver = role in ("APPROVER", "ADMIN")
    admin = role == "ADMIN"

    pages = {"업무": [], "관리": []}

    def P(fn, title, icon, url, default=False):
        return st.Page(fn, title=title, icon=icon, url_path=url, default=default)

    pages["업무"].append(P(dashboard.render, "대시보드", "📊", "dashboard", default=True))
    pages["업무"].append(P(purchase_request.render, "발주 요청", "🛒", "po-new"))
    if approver:
        pages["업무"].append(P(approval_box.render, "승인함", "✅", "approvals"))
    pages["업무"].append(P(purchase_list.render, "발주 현황", "📋", "po-list"))
    pages["업무"].append(P(invoice_intake.render, "명세서 입고", "🧾", "invoices"))
    pages["업무"].append(P(usage.render, "사용 등록", "✏️", "usage"))
    pages["업무"].append(P(stock.render, "재고 현황", "📦", "stock"))

    if approver:
        pages["관리"].append(P(payment.render, "결제 관리", "💳", "payments"))
        pages["관리"].append(P(vendor_status.render, "거래처 현황", "🏢", "vendors"))
        pages["관리"].append(P(master_data.render, "거래처·품목 관리", "🗂️", "master"))
    if admin:
        pages["관리"].append(P(user_admin.render, "사용자 관리", "👤", "users"))

    if not pages["관리"]:
        pages.pop("관리")
    return st.navigation(pages)


def main():
    user = st.session_state.get("user")
    if not user:
        login_view()
        return

    with st.sidebar:
        st.markdown(f"### 🏥 {ORG_NAME}")
        st.markdown(f"**{user['name']}** · {user.get('position') or ''}")
        role_kr = {"REQUESTER": "요청자", "APPROVER": "결재자", "ADMIN": "관리자"}
        st.caption(f"권한: {role_kr.get(user['role'], user['role'])}")
        if st.button("로그아웃", use_container_width=True):
            st.session_state.pop("user", None)
            st.rerun()
        st.divider()

    nav = build_nav(user)
    nav.run()


main()
