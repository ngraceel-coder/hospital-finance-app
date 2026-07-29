"""엑셀 내보내기 (세무 제출용 월별 정산표 등).

pandas + openpyxl. 반환은 bytes (Streamlit download_button 용).
"""
import io


def _to_xlsx_bytes(sheets: dict) -> bytes:
    """sheets: {sheet_name: pandas.DataFrame} → xlsx bytes."""
    import pandas as pd

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    return buf.getvalue()


def vendor_monthly_xlsx() -> bytes:
    """거래처별 월별 정산 매트릭스."""
    import pandas as pd
    from core.report import vendor_monthly_matrix

    m = vendor_monthly_matrix()
    records = []
    for row in m["rows"]:
        rec = {"거래처": row["vendor_name"]}
        for month in m["months"]:
            rec[month] = row["cells"].get(month, 0)
        rec["합계"] = row["total"]
        records.append(rec)
    df = pd.DataFrame(records) if records else pd.DataFrame(columns=["거래처", "합계"])
    return _to_xlsx_bytes({"거래처별 월별정산": df})


def vendor_detail_xlsx(vendor_id: int) -> bytes:
    """특정 거래처 명세서 목록 + 결제 이력."""
    import pandas as pd
    from core.invoice import list_invoices
    from core.payment import list_payments

    invs = list_invoices(vendor_id=vendor_id)
    pays = list_payments(vendor_id=vendor_id)
    inv_df = pd.DataFrame([{
        "명세서번호": i.get("invoice_no"), "발행일": i.get("issue_date"),
        "상태": i.get("status"), "금액": i.get("total_amount"),
    } for i in invs]) or pd.DataFrame()
    pay_df = pd.DataFrame([{
        "지급일": p.get("paid_at", "")[:10], "금액": p.get("amount"),
        "방법": p.get("method"), "담당": p.get("handler_name"),
    } for p in pays]) or pd.DataFrame()
    return _to_xlsx_bytes({"명세서": inv_df, "결제이력": pay_df})


def stock_xlsx() -> bytes:
    """재고 현황."""
    import pandas as pd
    from core.inventory import stock_overview

    rows = stock_overview()
    df = pd.DataFrame([{
        "분류": r["category"], "품목": r["name"], "규격": r["spec"],
        "단위": r["unit"], "현재고": r["stock"], "안전재고": r["safety_stock"],
        "부족분": r["shortage"],
    } for r in rows])
    return _to_xlsx_bytes({"재고현황": df})


def items_template_xlsx() -> bytes:
    """품목 일괄 업로드용 템플릿."""
    import pandas as pd

    df = pd.DataFrame(columns=[
        "name", "spec", "unit", "category", "unit_price", "safety_stock"])
    return _to_xlsx_bytes({"items": df})


def parse_items_upload(file) -> list:
    """업로드된 엑셀 → 품목 dict 리스트."""
    import pandas as pd

    df = pd.read_excel(file)
    out = []
    for _, r in df.iterrows():
        if pd.isna(r.get("name")):
            continue
        out.append({
            "name": str(r["name"]).strip(),
            "spec": "" if pd.isna(r.get("spec")) else str(r.get("spec")).strip(),
            "unit": "EA" if pd.isna(r.get("unit")) else str(r.get("unit")).strip(),
            "category": "소모품" if pd.isna(r.get("category")) else str(r.get("category")).strip(),
            "unit_price": 0 if pd.isna(r.get("unit_price")) else int(r.get("unit_price")),
            "safety_stock": 0 if pd.isna(r.get("safety_stock")) else float(r.get("safety_stock")),
        })
    return out
