# 🏥 병원 구매·재고 관리 앱

온소아청소년과의원(온자람실) 로컬 구매·재고 관리 시스템.
**발주 요청 → 원장 결재 → 명세서 스캔 입고 → 재고 관리 → 대금 결제**까지 하나의 앱에서 처리합니다.

> 용어 구분(중요): **결재(approval)** = 원장이 발주를 승인하는 행위 ·
> **결제(payment)** = 거래처에 대금을 지급하는 행위. 코드·화면에서 절대 섞지 않습니다.

---

## 빠른 시작

```bash
cd hospital_purchase
pip install -r requirements.txt          # 최초 1회
cp .env.example .env                      # 필요 값 입력(OCR은 6단계부터)
streamlit run app.py                      # 실행
# 내부망(다른 PC/태블릿)에서 접속 허용:
# streamlit run app.py --server.address 0.0.0.0
```

- 첫 실행 시 DB 스키마가 자동 생성되고 **관리자 계정 `admin / admin1234`** 이 만들어집니다.
  로그인 후 **사용자 관리 → 비밀번호 초기화**로 즉시 변경하세요.
- 데모 데이터로 화면을 둘러보려면: `PYTHONPATH=. python3 -m db.seed_demo`
  (계정: `director/pw1234`, `nurse/pw1234` 추가 생성)

### 인터넷 / 오프라인
- OCR(명세서 자동 인식)만 Anthropic API 호출이 필요합니다.
- API 키가 없어도 앱은 정상 동작하며, 명세서는 **수동 입력**으로 입고할 수 있습니다.
- OpenCV 미설치 환경에서도 품질검사/보정을 건너뛰고 원본으로 진행합니다(자동 감지).

---

## 핵심 비즈니스 규칙 (구현됨)

| 규칙 | 내용 | 구현 위치 |
|---|---|---|
| R1 | 재고는 계산값 (`SUM(stock_movements.qty)`), 재고 컬럼 없음 | `core/inventory.py` |
| R2 | 승인(APPROVED/RECEIVING) 발주에만 명세서 연결 | `core/invoice.py` `_assert_receivable` |
| R3 | 승인된 발주는 수정 불가 → 취소 후 재발주 | `core/purchase.py` `update_draft` |
| R4 | 본인 발주 본인 승인 금지(원장 셀프승인은 설정) | `core/purchase.py` `approve` |
| R5 | 결재는 체크만, `approver_id`/`approved_at` 자동 기록 | `core/purchase.py` |
| R6 | 사용자 삭제 금지 → 비활성화만 | `core/auth.py` `set_active` |
| R7 | OCR 결과 자동 확정 금지 → 사람이 확정해야 재고 반영 | `core/invoice.py` `confirm` |
| R8 | 명세서 확정은 1회성, 오확정은 역분개(ADJUST) | `core/invoice.py` `reverse_confirmed` |
| R9 | 미결제 = 확정 명세서 합계 − 결제 배분 합계 | `core/payment.py` |
| R10 | 모든 행위에 `user_id` 기록(`approval_logs`) | 전역 |

이 규칙들은 `tests_smoke.py` 에서 자동 검증합니다:

```bash
PYTHONPATH=. python3 tests_smoke.py
```

---

## 워크플로우

```
발주 작성 ─임시저장→ DRAFT
          └결재요청→ PENDING ─승인→ APPROVED ─입고→ RECEIVING ─전량→ CLOSED
                        └반려→ REJECTED ─수정→ PENDING(재요청)
```

명세서 입고 파이프라인: `업로드 → 품질검사 → 보정 → OCR → 품목매칭 → 3-way 매칭 → 검수 → 확정`

3-way 매칭 신호등: 🟢 통과 · 🟡 부분입고/단가불일치/직접구매 · 🔴 발주초과/미매칭(확정 차단)

---

## 프로젝트 구조

```
hospital_purchase/
├── app.py               # 진입점 · 로그인 · 역할별 네비게이션
├── config.py            # 설정(.env 로 덮어쓰기)
├── db/                  # schema.sql, connection, init_db, queries, seed_demo
├── core/                # auth, purchase, inventory, invoice, matching, payment, report
├── ocr/                 # preprocess(품질/보정), vision(Claude), prompts, pipeline
├── screens/             # 11개 화면(역할별 노출)
├── utils/               # helpers, backup, excel, pdf
├── data/hospital.db     # SQLite (자동 생성 · git 제외)
├── backup/              # 시작 시 자동 백업(30일 보관)
└── files/               # 명세서 원본/보정본(거래처/월별)
```

## 역할별 화면 (계획서 7.1)

| 화면 | 요청자 | 결재자 | 관리자 |
|---|:-:|:-:|:-:|
| 대시보드 / 발주요청 / 명세서입고 / 사용등록 / 재고현황 / 발주현황 | ○ | ○ | ○ |
| 승인함 | ✕ | ○ | ○ |
| 결제관리 / 거래처현황 / 거래처·품목관리 | ✕ | ○ | ○ |
| 사용자관리 | ✕ | ✕ | ○ |

---

## 코딩 규약 (계획서 10장 준수)
- 날짜: ISO 8601 문자열(KST) · 금액: 정수(원) · 수량: REAL(0.5 등 허용)
- 다중 테이블 작업(발주 승인, 명세서 확정, 결제)은 트랜잭션(`db/connection.transaction`)
- 쓰기 후 `st.cache_data.clear()` 호출 · API 키는 `.env`
- 앱 시작 시 DB 자동 백업(`backup/hospital_YYYYMMDD.db`, 30일 보관)

## 개발 단계 대비 현황
계획서 9장의 1~9단계 기능이 모두 구현되어 있습니다(로그인·사용자관리 → 기준정보 →
발주/결재 → 수동입고/재고 → 사용/안전재고 → 명세서 OCR·검수 → 별칭학습/3-way →
결제/미결제 → 거래처 월별현황·엑셀).
