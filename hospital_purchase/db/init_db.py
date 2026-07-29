"""DB 초기화 + 관리자 계정 생성.

앱 시작 시 ensure_db() 를 호출하면 스키마가 없을 때만 생성한다(멱등).
직접 실행하면 강제 초기화 + 샘플 관리자 계정을 만든다.
"""
import sqlite3

from config import DB_PATH, SCHEMA_PATH, ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_NAME


def _apply_schema(conn: sqlite3.Connection):
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())


def _has_tables(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()
    return row is not None


def ensure_db():
    """스키마와 관리자 계정을 보장. 이미 있으면 아무것도 하지 않는다."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        _apply_schema(conn)  # CREATE TABLE IF NOT EXISTS 라 안전
        conn.commit()
        # 관리자 계정 없으면 생성
        n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if n == 0:
            _create_admin(conn)
            conn.commit()
    finally:
        conn.close()


def _create_admin(conn: sqlite3.Connection):
    from core.auth import hash_password
    from utils.helpers import now_iso

    conn.execute(
        """INSERT INTO users(username, password_hash, name, position, role,
                             is_active, created_at)
           VALUES(?,?,?,?, 'ADMIN', 1, ?)""",
        (ADMIN_USERNAME, hash_password(ADMIN_PASSWORD), ADMIN_NAME, "행정", now_iso()),
    )
    print(f"[init_db] 관리자 계정 생성: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")


def reset_all():
    """모든 테이블 삭제 후 재생성(개발용)."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        for t in tables:
            conn.execute(f"DROP TABLE IF EXISTS {t}")
        conn.commit()
    finally:
        conn.close()
    ensure_db()


if __name__ == "__main__":
    import sys

    if "--reset" in sys.argv:
        reset_all()
        print("[init_db] 초기화 완료(reset).")
    else:
        ensure_db()
        print("[init_db] 스키마 준비 완료.")
