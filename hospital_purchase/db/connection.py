"""SQLite 연결 관리.

- 외래키 제약을 항상 켠다(ON DELETE CASCADE 동작 보장).
- row_factory 로 컬럼명 접근(dict-like).
- 트랜잭션은 `with transaction() as conn:` 컨텍스트로 사용한다(계획서 10-4).
"""
import sqlite3
from contextlib import contextmanager

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction():
    """여러 테이블을 건드리는 작업은 이 컨텍스트로 원자성 보장.

    예: 명세서 확정, 발주 승인.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def cursor():
    """단순 조회/단일 쓰기용 커넥션."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
