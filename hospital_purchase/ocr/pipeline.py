"""명세서 스캔 입고 파이프라인 오케스트레이션 (계획서 6.1).

업로드 → 품질검사 → 보정 → OCR → 품목매칭 → (검수 화면으로 전달할) 초안 생성.
파일은 files/{거래처명}/{YYYY-MM}/ 아래 원본·보정본으로 보관.
"""
import re
from pathlib import Path

from config import FILES_DIR
from utils.helpers import today_iso, parse_amount
from ocr import preprocess, vision
from core import matching


def _safe(name: str) -> str:
    return re.sub(r"[^\w가-힣.-]+", "_", (name or "unknown")).strip("_") or "unknown"


def save_upload(uploaded_bytes: bytes, vendor_name: str, filename: str) -> Path:
    """업로드 원본을 files/{거래처}/{YYYY-MM}/ 에 저장하고 경로 반환."""
    month = today_iso()[:7]
    folder = FILES_DIR / _safe(vendor_name) / month
    folder.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix or ".jpg"
    base = _safe(Path(filename).stem)
    dest = folder / f"{base}_original{ext}"
    n = 1
    while dest.exists():
        dest = folder / f"{base}_{n}_original{ext}"
        n += 1
    dest.write_bytes(uploaded_bytes)
    return dest


def process(original_path, vendor: dict):
    """전처리 + OCR + 매칭. 반환:
      {
        quality: {...},
        processed_path: str|None,
        ocr: {...}|None,
        ocr_error: str|None,
        items: [ {ocr_item_name, item_id, qty, unit_price, amount, lot_no,
                  expiry_date, match_status, candidates:[...]} ],
        header: {invoice_no, issue_date, total_amount},
      }
    """
    original_path = str(original_path)
    quality = preprocess.quality_check(original_path)

    processed_path = None
    if preprocess.cv2_available():
        p = Path(original_path)
        out = str(p.with_name(p.stem.replace("_original", "") + "_processed.jpg"))
        try:
            processed_path = preprocess.enhance(original_path, out)
        except Exception:
            processed_path = None

    ocr_data, ocr_error = None, None
    target = processed_path or original_path
    if vision.vision_available():
        try:
            ocr_data = vision.run_ocr(target, vendor)
        except Exception as e:
            ocr_error = str(e)
    else:
        ocr_error = "Vision 미사용(anthropic/API키 없음). 수동 입력하세요."

    items = []
    header = {"invoice_no": None, "issue_date": None, "total_amount": 0}
    if ocr_data:
        header = {
            "invoice_no": ocr_data.get("invoice_no"),
            "issue_date": ocr_data.get("issue_date"),
            "total_amount": parse_amount(ocr_data.get("total_amount")),
        }
        for raw in ocr_data.get("items", []):
            name = raw.get("name", "")
            m = matching.match_item(name, vendor_id=vendor["id"])
            qty = float(raw.get("qty") or 0)
            unit_price = parse_amount(raw.get("unit_price"))
            amount = parse_amount(raw.get("amount")) or int(qty * unit_price)
            items.append({
                "ocr_item_name": name,
                "item_id": m["item_id"],
                "qty": qty,
                "unit_price": unit_price,
                "amount": amount,
                "lot_no": raw.get("lot_no"),
                "expiry_date": raw.get("expiry_date"),
                "match_status": m["status"],
                "candidates": m["candidates"],
            })
    return {
        "quality": quality,
        "processed_path": processed_path,
        "ocr": ocr_data,
        "ocr_error": ocr_error,
        "items": items,
        "header": header,
    }
