"""⑬ 사용자 관리 — 관리자 전용 (계획서 7.2). R6: 삭제 없이 비활성화만."""
import streamlit as st

from screens._shared import require, clear_cache
from core import auth

ROLE_KR = {"REQUESTER": "요청자", "APPROVER": "결재자", "ADMIN": "관리자"}


def render():
    me = require("ADMIN")
    st.title("👤 사용자 관리")

    st.subheader("사용자 등록")
    with st.form("new_user", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        username = c1.text_input("아이디 *")
        password = c2.text_input("초기 비밀번호 *", type="password")
        name = c3.text_input("이름 *")
        position = c1.selectbox("직책", auth.POSITIONS)
        role = c2.selectbox("역할 *", auth.ROLES,
                            format_func=lambda r: ROLE_KR.get(r, r))
        if st.form_submit_button("등록", type="primary"):
            try:
                if not (username and password and name):
                    raise ValueError("아이디/비밀번호/이름은 필수입니다.")
                auth.create_user(username, password, name, position, role)
                clear_cache(); st.success("사용자 등록 완료."); st.rerun()
            except Exception as e:
                st.error(str(e))

    st.divider()
    st.subheader("사용자 목록")
    st.caption("R6: 퇴사자는 삭제하지 않고 비활성화만 합니다(결재 이력 보존).")
    for u in auth.list_users():
        tag = "" if u["is_active"] else " · ⛔비활성"
        with st.expander(f"{u['name']} ({u['username']}) · "
                         f"{ROLE_KR.get(u['role'])}{tag}"):
            c1, c2 = st.columns(2)
            role = c1.selectbox("역할", auth.ROLES,
                                index=auth.ROLES.index(u["role"]),
                                format_func=lambda r: ROLE_KR.get(r, r),
                                key=f"role_{u['id']}")
            position = c2.selectbox(
                "직책", auth.POSITIONS,
                index=auth.POSITIONS.index(u["position"])
                if u["position"] in auth.POSITIONS else 0,
                key=f"pos_{u['id']}")
            b1, b2, b3 = st.columns(3)
            if b1.button("역할/직책 저장", key=f"usave_{u['id']}"):
                auth.update_user(u["id"], position=position, role=role)
                clear_cache(); st.success("저장됨."); st.rerun()
            if b2.button("비활성화" if u["is_active"] else "활성화",
                         key=f"uact_{u['id']}", disabled=(u["id"] == me["id"])):
                auth.set_active(u["id"], not u["is_active"])
                clear_cache(); st.rerun()
            newpw = b3.text_input("비밀번호 초기화", type="password",
                                  key=f"pw_{u['id']}")
            if b3.button("초기화 적용", key=f"pwbtn_{u['id']}"):
                if newpw:
                    auth.reset_password(u["id"], newpw)
                    st.success("비밀번호 변경됨.")
                else:
                    st.warning("새 비밀번호를 입력하세요.")
