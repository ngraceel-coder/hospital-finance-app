"""데모용 샘플 데이터 생성 (선택). 실제 운영 전 화면 확인용.

실행: PYTHONPATH=. python3 -m db.seed_demo
"""
from db.init_db import ensure_db
from core import auth, purchase, invoice, inventory
from core.auth import list_users
from db.queries import create_vendor, create_item


def seed():
    ensure_db()
    if len(list_users()) > 1:
        print("이미 사용자가 있습니다. 중복 생성을 피하기 위해 건너뜁니다.")
        return

    auth.create_user("nurse", "pw1234", "김간호", "간호사", "REQUESTER")
    auth.create_user("director", "pw1234", "노지혜", "원장", "APPROVER")
    nurse = auth.authenticate("nurse", "pw1234")
    director = auth.authenticate("director", "pw1234")

    v1 = create_vendor("온약품", payment_terms="말일결산 익월10일",
                       contact_person="박대리", phone="02-000-0000")
    v2 = create_vendor("자람메디칼", payment_terms="현금결제")

    saline = create_item("생리식염수", "병", "약품", spec="500ml",
                         default_vendor_id=v1, unit_price=1200, safety_stock=30)
    gauze = create_item("멸균거즈", "박스", "소모품", default_vendor_id=v1,
                        unit_price=5000, safety_stock=10)
    kit = create_item("독감 신속키트", "개", "검사키트", spec="25T",
                      default_vendor_id=v2, unit_price=800, safety_stock=50)

    po = purchase.create_po(v1, nurse["id"], [
        {"item_id": saline, "qty": 20, "unit_price": 1200},
        {"item_id": gauze, "qty": 5, "unit_price": 5000},
    ], memo="정기 발주", submit=True)
    purchase.approve(director, po)

    inv = invoice.create_invoice(
        v1, "files/demo.jpg", director["id"], invoice_no="ON-2607-01",
        issue_date="2026-07-20", po_id=po, total_amount=20 * 1200 + 5 * 5000,
        ocr_items=[
            {"ocr_item_name": "생리식염수500ml", "item_id": saline, "qty": 20,
             "unit_price": 1200, "amount": 24000, "lot_no": "L2604",
             "expiry_date": "2026-09-15", "match_status": "MATCHED"},
            {"ocr_item_name": "멸균거즈", "item_id": gauze, "qty": 5,
             "unit_price": 5000, "amount": 25000, "match_status": "MATCHED"},
        ])
    invoice.confirm(inv, director["id"], update_prices=True)
    inventory.use_item(saline, 15, nurse["id"], reason="진료 사용")

    print("데모 데이터 생성 완료.")
    print("  로그인: admin/admin1234 · director/pw1234 · nurse/pw1234")


if __name__ == "__main__":
    seed()
