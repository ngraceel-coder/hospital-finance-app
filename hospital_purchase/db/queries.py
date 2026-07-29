"""공통 조회/CRUD 함수 (거래처·품목·별칭·결재이력).

비즈니스 규칙이 얽힌 로직은 core/ 에 두고, 여기에는 단순 데이터 접근만 둔다.
"""
from db.connection import cursor
from utils.helpers import now_iso

CATEGORIES = ("약품", "소모품", "검사키트", "사무용품")


# ── 거래처 ─────────────────────────────────────────────────────────────
def create_vendor(name, business_no="", contact_person="", phone="", email="",
                  payment_terms="", memo=""):
    with cursor() as conn:
        cur = conn.execute(
            """INSERT INTO vendors(name, business_no, contact_person, phone, email,
                                   payment_terms, memo, is_active, created_at)
               VALUES(?,?,?,?,?,?,?,1,?)""",
            (name, business_no, contact_person, phone, email, payment_terms, memo,
             now_iso()),
        )
        return cur.lastrowid


def update_vendor(vendor_id, **fields):
    allowed = {"name", "business_no", "contact_person", "phone", "email",
               "payment_terms", "memo", "is_active"}
    sets, params = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k} = ?"); params.append(v)
    if not sets:
        return
    params.append(vendor_id)
    with cursor() as conn:
        conn.execute(f"UPDATE vendors SET {', '.join(sets)} WHERE id = ?", params)


def list_vendors(active_only=True):
    q = "SELECT * FROM vendors"
    if active_only:
        q += " WHERE is_active = 1"
    q += " ORDER BY name"
    with cursor() as conn:
        return [dict(r) for r in conn.execute(q).fetchall()]


def get_vendor(vendor_id):
    with cursor() as conn:
        r = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
    return dict(r) if r else None


# ── 품목 ───────────────────────────────────────────────────────────────
def create_item(name, unit, category, spec="", default_vendor_id=None,
                unit_price=0, safety_stock=0):
    with cursor() as conn:
        cur = conn.execute(
            """INSERT INTO items(name, spec, unit, category, default_vendor_id,
                                 unit_price, safety_stock, is_active, created_at)
               VALUES(?,?,?,?,?,?,?,1,?)""",
            (name, spec, unit, category, default_vendor_id, int(unit_price),
             float(safety_stock), now_iso()),
        )
        return cur.lastrowid


def update_item(item_id, **fields):
    allowed = {"name", "spec", "unit", "category", "default_vendor_id",
               "unit_price", "safety_stock", "is_active"}
    sets, params = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k} = ?"); params.append(v)
    if not sets:
        return
    params.append(item_id)
    with cursor() as conn:
        conn.execute(f"UPDATE items SET {', '.join(sets)} WHERE id = ?", params)


def list_items(active_only=True, vendor_id=None, category=None, search=None):
    q = "SELECT * FROM items WHERE 1=1"
    params = []
    if active_only:
        q += " AND is_active = 1"
    if vendor_id:
        q += " AND default_vendor_id = ?"; params.append(vendor_id)
    if category:
        q += " AND category = ?"; params.append(category)
    if search:
        q += " AND (name LIKE ? OR spec LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    q += " ORDER BY category, name"
    with cursor() as conn:
        return [dict(r) for r in conn.execute(q, params).fetchall()]


def get_item(item_id):
    with cursor() as conn:
        r = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return dict(r) if r else None


def set_item_price(item_id, unit_price):
    with cursor() as conn:
        conn.execute("UPDATE items SET unit_price = ? WHERE id = ?",
                     (int(unit_price), item_id))


# ── 품목 별칭 (OCR 학습) ───────────────────────────────────────────────
def add_alias(item_id, alias_text, vendor_id=None):
    """(vendor_id, alias_text) 유니크. 이미 있으면 무시."""
    with cursor() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO item_aliases(item_id, vendor_id, alias_text,
                                                  created_at)
               VALUES(?,?,?,?)""",
            (item_id, vendor_id, alias_text.strip(), now_iso()),
        )


def find_alias(alias_text, vendor_id=None):
    """완전 일치 별칭 조회. 거래처 특정 → 없으면 거래처 무관(NULL) 순."""
    with cursor() as conn:
        r = conn.execute(
            "SELECT item_id FROM item_aliases WHERE alias_text = ? AND vendor_id IS ?",
            (alias_text.strip(), vendor_id),
        ).fetchone()
        if not r:
            r = conn.execute(
                "SELECT item_id FROM item_aliases WHERE alias_text = ? AND vendor_id IS NULL",
                (alias_text.strip(),),
            ).fetchone()
    return r["item_id"] if r else None


# ── 결재 이력 ──────────────────────────────────────────────────────────
def log_action(doc_type, doc_id, action, user_id, comment="", conn=None):
    """approval_logs 한 줄 기록. 트랜잭션 안에서 쓰려면 conn 을 넘긴다."""
    sql = """INSERT INTO approval_logs(doc_type, doc_id, action, user_id, acted_at, comment)
             VALUES(?,?,?,?,?,?)"""
    args = (doc_type, doc_id, action, user_id, now_iso(), comment)
    if conn is not None:
        conn.execute(sql, args)
    else:
        with cursor() as c:
            c.execute(sql, args)


def get_logs(doc_type, doc_id):
    with cursor() as conn:
        rows = conn.execute(
            """SELECT l.*, u.name AS user_name, u.position
               FROM approval_logs l JOIN users u ON u.id = l.user_id
               WHERE doc_type = ? AND doc_id = ? ORDER BY acted_at""",
            (doc_type, doc_id),
        ).fetchall()
    return [dict(r) for r in rows]
