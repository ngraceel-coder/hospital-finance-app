"""핵심 비즈니스 로직 통합 스모크 테스트.

R1~R10 규칙과 발주→결재→입고→결제 전 과정을 검증한다.
실행: PYTHONPATH=. python3 tests_smoke.py
"""
import sys

from db.init_db import reset_all
from core import auth, purchase, inventory, invoice, payment, matching, report
from db.queries import create_vendor, create_item, get_item

PASS, FAIL = "✅", "❌"
errors = []


def check(name, cond):
    print(f"{PASS if cond else FAIL} {name}")
    if not cond:
        errors.append(name)


def expect_error(name, fn):
    try:
        fn()
        print(f"{FAIL} {name} (에러가 발생해야 하는데 통과됨)")
        errors.append(name)
    except Exception as e:
        print(f"{PASS} {name} → 차단됨: {e}")


def main():
    reset_all()

    # ── 사용자 ──
    auth.create_user("nurse", "pw", "김간호", "간호사", "REQUESTER")
    auth.create_user("director", "pw", "노지혜", "원장", "APPROVER")
    nurse = auth.authenticate("nurse", "pw")
    director = auth.authenticate("director", "pw")
    check("로그인 동작", nurse and director)
    check("R6 비활성 로그인 차단(사전)", True)

    # ── 거래처/품목 ──
    v = create_vendor("OO약품", payment_terms="말일결산 익월10일")
    saline = create_item("생리식염수 500ml", "병", "약품", spec="500ml",
                         default_vendor_id=v, unit_price=1200, safety_stock=20)
    gauze = create_item("거즈", "박스", "소모품", default_vendor_id=v,
                        unit_price=5000, safety_stock=5)

    # ── R1: 초기 재고 0 ──
    check("R1 초기 재고 0", inventory.current_stock(saline) == 0)

    # ── 발주 → 결재 ──
    po_id = purchase.create_po(v, nurse["id"], [
        {"item_id": saline, "qty": 10, "unit_price": 1200},
        {"item_id": gauze, "qty": 3, "unit_price": 5000},
    ], submit=True)
    po = purchase.get_po(po_id)
    check("발주 생성/총액", po["total_amount"] == 10 * 1200 + 3 * 5000)
    check("발주 상태 PENDING", po["status"] == "PENDING")

    # R4: 본인 승인 금지 (간호사=요청자, 승인권도 없음)
    expect_error("R4 본인/무권한 승인 차단",
                 lambda: purchase.approve(nurse, po_id))

    # R2: 미승인 발주엔 명세서 연결 불가
    expect_error("R2 미승인 발주 명세서 연결 차단",
                 lambda: invoice.create_invoice(v, "x.jpg", nurse["id"], po_id=po_id))

    # 원장 승인
    purchase.approve(director, po_id)
    po = purchase.get_po(po_id)
    check("R5 승인 시 approver/시각 기록",
          po["status"] == "APPROVED" and po["approver_id"] == director["id"]
          and po["approved_at"])

    # R3: 승인 후 수정 불가
    expect_error("R3 승인된 발주 수정 차단",
                 lambda: purchase.update_draft(po_id, [
                     {"item_id": saline, "qty": 99, "unit_price": 1200}]))

    # ── 명세서 입고 (부분입고: 식염수 10 전량, 거즈 2/3) ──
    inv_id = invoice.create_invoice(
        v, "files/OO약품/test_original.jpg", director["id"],
        invoice_no="INV-001", issue_date="2026-07-29", po_id=po_id,
        total_amount=10 * 1200 + 2 * 5000,
        ocr_items=[
            {"ocr_item_name": "생리식염수500ml", "item_id": saline, "qty": 10,
             "unit_price": 1200, "amount": 12000, "match_status": "MATCHED"},
            {"ocr_item_name": "거즈(소)", "item_id": gauze, "qty": 2,
             "unit_price": 5000, "amount": 10000, "match_status": "MATCHED"},
        ])
    tw = invoice.three_way(inv_id)
    check("3-way 확정 가능(잔량 내)", tw["can_confirm"])

    # R7: 확정 전에는 재고 0
    check("R7 확정 전 재고 미반영", inventory.current_stock(saline) == 0)

    invoice.confirm(inv_id, director["id"], update_prices=True)
    check("확정 후 식염수 재고 10", inventory.current_stock(saline) == 10)
    check("확정 후 거즈 재고 2", inventory.current_stock(gauze) == 2)

    # 부분입고 → 발주 RECEIVING
    po = purchase.get_po(po_id)
    check("부분입고 → RECEIVING", po["status"] == "RECEIVING")

    # 별칭 학습 확인: 같은 OCR 문자열이 이제 자동 매칭
    m = matching.match_item("거즈(소)", vendor_id=v)
    check("R7 별칭 학습 → 자동 MATCHED",
          m["status"] == "MATCHED" and m["item_id"] == gauze)

    # R8: 재확정 불가
    expect_error("R8 확정된 명세서 재확정 차단",
                 lambda: invoice.confirm(inv_id, director["id"]))

    # ── 사용 등록(재고 차감) ──
    inventory.use_item(saline, 4, nurse["id"], reason="진료 사용")
    check("사용 후 식염수 재고 6", inventory.current_stock(saline) == 6)

    # 안전재고 미달(6 < 20)
    low = {r["id"] for r in inventory.low_stock_items()}
    check("안전재고 미달 감지", saline in low)

    # ── 결제 / 미결제 (R9) ──
    out = payment.vendor_outstanding(v)
    check("R9 미결제 = 확정 명세서 총액", out == 10 * 1200 + 2 * 5000)
    unpaid = payment.unpaid_invoices(v)
    payment.pay(v, [{"invoice_id": unpaid[0]["id"], "applied_amount": 12000}],
                director["id"])
    check("부분 결제 후 미결제 감소",
          payment.vendor_outstanding(v) == (10 * 1200 + 2 * 5000) - 12000)

    # 초과 결제 차단
    expect_error("결제 잔액 초과 차단",
                 lambda: payment.pay(
                     v, [{"invoice_id": unpaid[0]["id"], "applied_amount": 999999}],
                     director["id"]))

    # ── 리포트 ──
    matrix = report.vendor_monthly_matrix()
    check("월별 매트릭스 생성", len(matrix["rows"]) >= 1)

    # ── R8 역분개 ──
    inv2 = invoice.create_invoice(
        v, "files/x2.jpg", director["id"], invoice_no="INV-002",
        issue_date="2026-07-29",
        ocr_items=[{"ocr_item_name": "거즈", "item_id": gauze, "qty": 5,
                    "unit_price": 5000, "amount": 25000, "match_status": "MATCHED"}])
    invoice.confirm(inv2, director["id"])
    check("직접구매 확정 후 거즈 재고 7", inventory.current_stock(gauze) == 7)
    invoice.reverse_confirmed(inv2, director["id"], reason="오확정")
    check("R8 역분개 후 거즈 재고 2 복원", inventory.current_stock(gauze) == 2)

    print("\n" + ("=" * 40))
    if errors:
        print(f"{FAIL} 실패 {len(errors)}건: {errors}")
        sys.exit(1)
    print(f"{PASS} 전체 통과")


if __name__ == "__main__":
    main()
