-- 병원 구매·재고 관리 앱 스키마 (계획서 3장)
-- 결재(approval)와 결제(payment)를 절대 섞지 않는다.

-- 1. 사용자
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    name            TEXT NOT NULL,
    position        TEXT,                       -- 원장/실장/간호사/행정
    role            TEXT NOT NULL,              -- REQUESTER/APPROVER/ADMIN
    is_active       INTEGER NOT NULL DEFAULT 1, -- 퇴사자는 0 (삭제 금지)
    created_at      TEXT NOT NULL
);

-- 2. 거래처
CREATE TABLE IF NOT EXISTS vendors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    business_no     TEXT,
    contact_person  TEXT,
    phone           TEXT,
    email           TEXT,
    payment_terms   TEXT,
    memo            TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL
);

-- 3. 품목 마스터
CREATE TABLE IF NOT EXISTS items (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    spec              TEXT,
    unit              TEXT NOT NULL,
    category          TEXT NOT NULL,
    default_vendor_id INTEGER REFERENCES vendors(id),
    unit_price        INTEGER DEFAULT 0,
    safety_stock      REAL DEFAULT 0,
    is_active         INTEGER NOT NULL DEFAULT 1,
    created_at        TEXT NOT NULL
);

-- 4. 품목 별칭 (OCR 매칭 학습용)
CREATE TABLE IF NOT EXISTS item_aliases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id     INTEGER NOT NULL REFERENCES items(id),
    vendor_id   INTEGER REFERENCES vendors(id),
    alias_text  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    UNIQUE(vendor_id, alias_text)
);

-- 5. 발주
CREATE TABLE IF NOT EXISTS purchase_orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    po_number     TEXT NOT NULL UNIQUE,
    vendor_id     INTEGER NOT NULL REFERENCES vendors(id),
    requester_id  INTEGER NOT NULL REFERENCES users(id),
    requested_at  TEXT NOT NULL,
    status        TEXT NOT NULL,
    approver_id   INTEGER REFERENCES users(id),
    approved_at   TEXT,
    reject_reason TEXT,
    total_amount  INTEGER NOT NULL DEFAULT 0,
    memo          TEXT
);

-- 6. 발주 상세
CREATE TABLE IF NOT EXISTS po_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id        INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    item_id      INTEGER NOT NULL REFERENCES items(id),
    qty          REAL NOT NULL,
    unit_price   INTEGER NOT NULL,
    amount       INTEGER NOT NULL,
    received_qty REAL NOT NULL DEFAULT 0
);

-- 7. 결재 이력
CREATE TABLE IF NOT EXISTS approval_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_type    TEXT NOT NULL,                   -- PO / INVOICE
    doc_id      INTEGER NOT NULL,
    action      TEXT NOT NULL,                   -- REQUEST/APPROVE/REJECT/RESUBMIT/CANCEL/CONFIRM
    user_id     INTEGER NOT NULL REFERENCES users(id),
    acted_at    TEXT NOT NULL,
    comment     TEXT
);

-- 8. 거래명세서
CREATE TABLE IF NOT EXISTS invoices (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id      INTEGER NOT NULL REFERENCES vendors(id),
    invoice_no     TEXT,
    issue_date     TEXT,
    po_id          INTEGER REFERENCES purchase_orders(id),
    original_file  TEXT NOT NULL,
    processed_file TEXT,
    ocr_raw        TEXT,
    status         TEXT NOT NULL,                -- PENDING_REVIEW/CONFIRMED/REJECTED
    total_amount   INTEGER DEFAULT 0,
    handler_id     INTEGER REFERENCES users(id),
    confirmed_at   TEXT,
    created_at     TEXT NOT NULL
);

-- 9. 명세서 상세
CREATE TABLE IF NOT EXISTS invoice_items (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id     INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    ocr_item_name  TEXT NOT NULL,
    item_id        INTEGER REFERENCES items(id),
    qty            REAL NOT NULL,
    unit_price     INTEGER NOT NULL,
    amount         INTEGER NOT NULL,
    lot_no         TEXT,
    expiry_date    TEXT,
    match_status   TEXT NOT NULL                 -- MATCHED/AMBIGUOUS/UNMATCHED/NEW
);

-- 10. 재고 이동 (재고의 유일한 원천)
CREATE TABLE IF NOT EXISTS stock_movements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id     INTEGER NOT NULL REFERENCES items(id),
    move_type   TEXT NOT NULL,                   -- IN/USE/DISPOSE/ADJUST
    qty         REAL NOT NULL,                   -- 입고 +, 사용/폐기 -
    moved_at    TEXT NOT NULL,
    ref_type    TEXT,                            -- INVOICE/MANUAL
    ref_id      INTEGER,
    lot_no      TEXT,
    expiry_date TEXT,
    reason      TEXT,
    user_id     INTEGER NOT NULL REFERENCES users(id)
);

-- 11. 결제(대금 지급)
CREATE TABLE IF NOT EXISTS payments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id   INTEGER NOT NULL REFERENCES vendors(id),
    paid_at     TEXT NOT NULL,
    amount      INTEGER NOT NULL,
    method      TEXT,
    handler_id  INTEGER NOT NULL REFERENCES users(id),
    memo        TEXT,
    created_at  TEXT NOT NULL
);

-- 12. 결제-명세서 연결
CREATE TABLE IF NOT EXISTS payment_invoices (
    payment_id     INTEGER NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
    invoice_id     INTEGER NOT NULL REFERENCES invoices(id),
    applied_amount INTEGER NOT NULL,
    PRIMARY KEY (payment_id, invoice_id)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_sm_item   ON stock_movements(item_id, moved_at);
CREATE INDEX IF NOT EXISTS idx_po_status ON purchase_orders(status, requested_at);
CREATE INDEX IF NOT EXISTS idx_inv_vendor ON invoices(vendor_id, issue_date);
CREATE INDEX IF NOT EXISTS idx_alias     ON item_aliases(vendor_id, alias_text);
