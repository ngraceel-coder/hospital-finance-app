"""인증·권한.

- 비밀번호는 bcrypt 해시로만 저장(계획서 2장).
- 사용자 삭제 금지: 비활성화(is_active=0)만 허용(R6).
- 역할: REQUESTER / APPROVER / ADMIN.
"""
from db.connection import cursor
from utils.helpers import now_iso

ROLES = ("REQUESTER", "APPROVER", "ADMIN")
POSITIONS = ("원장", "실장", "간호사", "행정")

# 역할 계층: ADMIN ⊇ APPROVER ⊇ REQUESTER
_ROLE_RANK = {"REQUESTER": 1, "APPROVER": 2, "ADMIN": 3}


# ── 비밀번호 해시 ──────────────────────────────────────────────────────
# bcrypt 를 직접 사용한다. (passlib 1.7.x + bcrypt 4.x 백엔드 자체검사 버그 회피)
# bcrypt 는 72바이트를 넘는 입력을 거부하므로 안전하게 잘라서 넘긴다.
def _pw_bytes(plain: str) -> bytes:
    return plain.encode("utf-8")[:72]


def hash_password(plain: str) -> str:
    import bcrypt

    return bcrypt.hashpw(_pw_bytes(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    import bcrypt

    try:
        return bcrypt.checkpw(_pw_bytes(plain), hashed.encode("utf-8"))
    except Exception:
        return False


# ── 로그인 ─────────────────────────────────────────────────────────────
def authenticate(username: str, password: str):
    """성공 시 사용자 dict, 실패 시 None. 비활성 계정은 로그인 불가."""
    with cursor() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,),
        ).fetchone()
    if not row:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return dict(row)


# ── 권한 체크 ──────────────────────────────────────────────────────────
def has_role(user: dict, required: str) -> bool:
    if not user:
        return False
    return _ROLE_RANK.get(user.get("role"), 0) >= _ROLE_RANK.get(required, 99)


def can_approve(user: dict) -> bool:
    return has_role(user, "APPROVER")


def is_admin(user: dict) -> bool:
    return user and user.get("role") == "ADMIN"


# ── 사용자 CRUD ────────────────────────────────────────────────────────
def create_user(username, password, name, position, role):
    if role not in ROLES:
        raise ValueError(f"알 수 없는 역할: {role}")
    with cursor() as conn:
        exists = conn.execute(
            "SELECT 1 FROM users WHERE username = ?", (username,)
        ).fetchone()
        if exists:
            raise ValueError(f"이미 존재하는 아이디입니다: {username}")
        conn.execute(
            """INSERT INTO users(username, password_hash, name, position, role,
                                 is_active, created_at)
               VALUES(?,?,?,?,?,1,?)""",
            (username, hash_password(password), name, position, role, now_iso()),
        )


def list_users(active_only=False):
    q = "SELECT * FROM users"
    if active_only:
        q += " WHERE is_active = 1"
    q += " ORDER BY is_active DESC, name"
    with cursor() as conn:
        return [dict(r) for r in conn.execute(q).fetchall()]


def get_user(user_id):
    with cursor() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def update_role(user_id, role):
    if role not in ROLES:
        raise ValueError(f"알 수 없는 역할: {role}")
    with cursor() as conn:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))


def update_user(user_id, name=None, position=None, role=None):
    fields, params = [], []
    if name is not None:
        fields.append("name = ?"); params.append(name)
    if position is not None:
        fields.append("position = ?"); params.append(position)
    if role is not None:
        if role not in ROLES:
            raise ValueError(f"알 수 없는 역할: {role}")
        fields.append("role = ?"); params.append(role)
    if not fields:
        return
    params.append(user_id)
    with cursor() as conn:
        conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", params)


def set_active(user_id, active: bool):
    """R6: 삭제 대신 비활성화만."""
    with cursor() as conn:
        conn.execute(
            "UPDATE users SET is_active = ? WHERE id = ?", (1 if active else 0, user_id)
        )


def reset_password(user_id, new_password):
    with cursor() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), user_id),
        )
