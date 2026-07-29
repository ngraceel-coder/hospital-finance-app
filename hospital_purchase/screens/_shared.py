"""화면 공통 헬퍼: 세션/사용자, 캐시, 포맷, 권한 가드."""
import streamlit as st

from core.auth import has_role
from utils.helpers import fmt_won, fmt_qty  # re-export


def current_user():
    return st.session_state.get("user")


def require(role="REQUESTER"):
    """페이지 진입 가드. 권한 없으면 안내 후 중단."""
    user = current_user()
    if not user:
        st.warning("로그인이 필요합니다.")
        st.stop()
    if not has_role(user, role):
        st.error("이 화면에 접근할 권한이 없습니다.")
        st.stop()
    return user


def clear_cache():
    """쓰기 후 조회 캐시 무효화 (계획서 10-5)."""
    try:
        st.cache_data.clear()
    except Exception:
        pass


def toast_ok(msg):
    clear_cache()
    st.success(msg)


def page_title(title, icon=""):
    st.title(f"{icon} {title}".strip())
