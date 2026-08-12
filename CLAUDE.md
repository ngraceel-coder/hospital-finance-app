# CLAUDE.md

Guidance for AI assistants (Claude Code and others) working in this repository.

## Overview

This repository hosts **two independent applications** for **온소아청소년과의원 (온자람실)**, a Korean pediatric clinic. Both apps and their UI are Korean-language; keep user-facing strings, comments, and commit messages consistent with the existing Korean style.

| App | Directory | Stack | Purpose |
|---|---|---|---|
| **재정관리 (Finance)** | `hospital-finance-app/` | Next.js 14 (App Router) + Notion backend | Income/expense tracking, monthly checklist, budget settings, receipt OCR |
| **구매·재고 관리 (Purchase/Inventory)** | `hospital_purchase/` | Streamlit + SQLite | Purchase requisition → approval → invoice-scan intake → inventory → payment |

The two apps **do not share code**. Treat each directory as a separate project with its own dependencies, run commands, and conventions.

> **Domain terminology (critical):** In the purchase app, **결재 (approval)** = the director approving a purchase order, and **결제 (payment)** = paying a vendor. These are never mixed in code or UI. Keep the distinction when writing or translating.

### Loose top-level artifacts (do not treat as source of truth)

`hospital-finance-app.jsx`, `hospital-finance-app.html`, `hospital-finance-app.zip` (empty), and `ziUrdDof` (a zip archive) are prototype/export snapshots of the finance app. The **maintained** finance code lives in `hospital-finance-app/`. Do not edit the loose files to change app behavior.

---

## Finance app — `hospital-finance-app/`

Next.js 14 App Router application. **Notion databases are the backend** (no SQL DB); OpenAI provides receipt OCR.

### Run

```bash
cd hospital-finance-app
npm install
npm run dev      # local dev
npm run build    # production build
npm run start    # serve production build
```

Deployment target is **Vercel**. See `hospital-finance-app/README.md` for the full Notion + Vercel setup walkthrough (Korean).

### Structure

```
hospital-finance-app/
├── app/
│   ├── layout.js          # root layout (lang="ko")
│   ├── page.js            # entire client UI (single ~975-line page component)
│   ├── globals.css        # Tailwind styles
│   └── api/               # route handlers
│       ├── auth/route.js        # password login → JWT (7d)
│       ├── transactions/route.js
│       ├── checklist/route.js
│       ├── settings/route.js
│       └── ocr/route.js         # GPT-4o-mini vision OCR of bank screenshots
├── lib/notion.js          # ALL Notion CRUD helpers
├── package.json
├── next.config.js         # experimental.serverActions
└── tailwind.config.js
```

### Conventions

- **All Notion access goes through `lib/notion.js`.** Add new data operations as exported helpers there rather than calling `@notionhq/client` from route handlers directly. Helpers return `[]` on read failure and `{ success, error }` on write failure — follow that shape.
- **Notion property names are Korean and positional** (e.g. `'날짜'`, `'구분'`, `'금액'`, `'분류'`). They must match the actual Notion database schema documented in the README. Deletes are soft (`archived: true`), never hard deletes.
- **Three Notion databases**, each keyed by an env var: transactions (`NOTION_TRANSACTIONS_DB`), checklist (`NOTION_CHECKLIST_DB`), settings/budget (`NOTION_SETTINGS_DB`).
- **API routes** are thin: parse request → call a `lib/notion.js` helper → `NextResponse.json(...)`. Errors return `{ error: message }` with an appropriate status.
- **Auth**: `POST /api/auth` checks `LOGIN_PASSWORD` and issues a JWT signed with `JWT_SECRET`; `GET /api/auth` verifies the `Authorization: Bearer <token>` header.
- **OCR** (`/api/ocr`): uses OpenAI `gpt-4o-mini` (chosen for cost — ~1–4 KRW/image) to extract bank-transaction JSON from an uploaded image. The prompt embeds the clinic's auto-categorization keyword rules; keep those rules in sync if categories change. The route strips ```json fences and parses the first `{...}` block.

### Required environment variables (finance)

Set in Vercel (or `.env.local` for dev). None are committed.

```
NOTION_API_KEY
NOTION_TRANSACTIONS_DB
NOTION_CHECKLIST_DB
NOTION_SETTINGS_DB
OPENAI_API_KEY
LOGIN_PASSWORD
JWT_SECRET
```

---

## Purchase/Inventory app — `hospital_purchase/`

Local-first Streamlit app over SQLite. Runs on the clinic's network; only OCR needs the internet.

### Run

```bash
cd hospital_purchase
pip install -r requirements.txt        # first time
cp .env.example .env                   # fill values (OCR optional)
streamlit run app.py                   # http://localhost:8501
streamlit run app.py --server.address 0.0.0.0   # share on LAN

PYTHONPATH=. python3 -m db.seed_demo   # load demo data (director/pw1234, nurse/pw1234)
PYTHONPATH=. python3 tests_smoke.py    # run the smoke tests (see below)
```

First launch auto-creates the schema and an admin account **`admin / admin1234`** (change it immediately via 사용자 관리). App boot also runs `ensure_db()` and `auto_backup()` once per session.

### Structure

```
hospital_purchase/
├── app.py               # entry point · login · role-based navigation (st.Page)
├── config.py            # all settings/constants; overridable via .env
├── db/
│   ├── schema.sql       # 12 tables (see below)
│   ├── connection.py    # get_connection / transaction() / cursor()
│   ├── init_db.py       # ensure_db()
│   ├── queries.py       # shared read queries
│   └── seed_demo.py
├── core/                # business logic — auth, purchase, inventory,
│                        #   invoice, matching, payment, report
├── ocr/                 # preprocess (quality/deskew), vision (Claude), prompts, pipeline
├── screens/             # 11 Streamlit screens, exposed by role
├── utils/               # helpers, backup, excel, pdf
├── data/hospital.db     # SQLite (auto-created, git-ignored)
├── backup/              # startup auto-backups (30-day retention, git-ignored)
├── files/               # invoice originals/corrected scans (git-ignored)
└── tests_smoke.py       # business-rule verification
```

Layering: **`screens/` (UI) → `core/` (business logic) → `db/` (persistence).** Put business rules in `core/`, not in screen code. Screens are gated by role in `app.py:build_nav`.

### Database tables (`db/schema.sql`)

`users`, `vendors`, `items`, `item_aliases`, `purchase_orders`, `po_items`, `approval_logs`, `invoices`, `invoice_items`, `stock_movements`, `payments`, `payment_invoices`.

Note: **there is no stock quantity column.** Inventory is always a computed value — `SUM(stock_movements.qty)` (rule R1).

### Core business rules (enforced in code; verified by `tests_smoke.py`)

| Rule | Meaning | Location |
|---|---|---|
| R1 | Stock is computed (`SUM(stock_movements.qty)`), never stored | `core/inventory.py` |
| R2 | Invoices attach only to APPROVED/RECEIVING orders | `core/invoice.py` `_assert_receivable` |
| R3 | Approved orders are immutable → cancel & re-order | `core/purchase.py` `update_draft` |
| R4 | No self-approval (director self-approve is a config flag) | `core/purchase.py` `approve` |
| R5 | Approval records `approver_id`/`approved_at` automatically | `core/purchase.py` |
| R6 | Users are deactivated, never deleted | `core/auth.py` `set_active` |
| R7 | OCR results never auto-confirm; a human must confirm before stock moves | `core/invoice.py` `confirm` |
| R8 | Confirmation is one-shot; mistakes are reversed via ADJUST entries | `core/invoice.py` `reverse_confirmed` |
| R9 | Unpaid = confirmed invoice total − allocated payments | `core/payment.py` |
| R10 | Every action logs `user_id` (`approval_logs`) | everywhere |

**When changing `core/` logic, re-run `PYTHONPATH=. python3 tests_smoke.py` and keep all rules green.**

### Workflow

```
Purchase order:  DRAFT ─request→ PENDING ─approve→ APPROVED ─receive→ RECEIVING ─full→ CLOSED
                              └reject→ REJECTED ─edit→ PENDING (re-request)

Invoice intake:  upload → quality-check → correct → OCR → item-match → 3-way match → review → confirm
```

3-way match indicators: 🟢 pass · 🟡 partial receipt / price mismatch / direct purchase · 🔴 over-order / no match (blocks confirmation).

### Coding conventions (purchase app)

- **Dates**: ISO 8601 strings (KST). **Amounts**: integer KRW. **Quantities**: REAL (0.5 allowed).
- **Multi-table writes** (order approval, invoice confirmation, payment) must use `with transaction() as conn:` from `db/connection.py` for atomicity. Foreign keys are enforced (`PRAGMA foreign_keys = ON`).
- **After any write, call `st.cache_data.clear()`** so screens reflect fresh data.
- **Config lives in `config.py`** and is overridable via `.env` — do not hardcode paths, thresholds, or credentials elsewhere.
- **OCR** uses Anthropic (`VISION_MODEL`, default `claude-sonnet-5`). The app runs fully without an API key (manual invoice entry). OpenCV is optional — quality-check/correction is skipped gracefully if it is missing.

### Required / notable environment variables (purchase)

All optional (sensible defaults in `config.py`); set in `.env`:

```
HOSPITAL_DB_PATH, ORG_NAME, ORG_UNIT
ALLOW_DIRECTOR_SELF_APPROVE, AMOUNT_BASED_APPROVAL, APPROVAL_AMOUNT_THRESHOLD
EXPIRY_ALERT_DAYS
ANTHROPIC_API_KEY, VISION_MODEL, MIN_SHORT_EDGE_PX, BLUR_LAPLACIAN_MIN
MATCH_STRONG, MATCH_WEAK
BACKUP_RETENTION_DAYS
ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_NAME
```

---

## Git & workflow conventions

- **Never commit secrets or generated data.** `.env`, `data/*.db`, `backup/*.db`, and `files/**` are git-ignored in `hospital_purchase/`. The finance app's env vars live only in Vercel/`.env.local`.
- Commit messages in this repo are written in **Korean** and describe the change concisely (see `git log`).
- Do not create pull requests unless explicitly asked.
- There is no repo-wide CI, linter, or formatter configured. The only automated check is the purchase app's `tests_smoke.py` — run it after touching `hospital_purchase/core/` or `db/`.

## Quick checklist before finishing a change

- Finance: does data access go through `lib/notion.js`? Do Notion property names match the README schema? Did you avoid touching the loose top-level snapshot files?
- Purchase: did you keep business logic in `core/`, use `transaction()` for multi-table writes, clear the cache after writes, and pass `tests_smoke.py`?
- Both: Korean user-facing text and commit message; no secrets committed.
