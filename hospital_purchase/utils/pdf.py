"""발주서 PDF 생성 (계획서 R5).

하단 결재란 표기:
  요청  간호사 김OO   2026-07-29 14:20
  결재  원장  노지혜   2026-07-29 16:05  ✓ 승인

reportlab 사용. 한글 폰트가 없으면 기본 폰트로 대체(깨질 수 있어 경고).
반환은 bytes.
"""
import io

from config import ORG_NAME, ORG_UNIT
from utils.helpers import fmt_won, fmt_qty


def _register_korean_font():
    """시스템에 있을 법한 한글 TTF 를 찾아 등록. 실패하면 None."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os

    candidates = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/Library/Fonts/AppleGothic.ttf",
        "C:/Windows/Fonts/malgun.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("KFont", path))
                return "KFont"
            except Exception:
                continue
    return None


def po_pdf(po: dict, items: list, logs: list) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    font = _register_korean_font() or "Helvetica"
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 25 * mm

    c.setFont(font, 16)
    c.drawCentredString(w / 2, y, "발 주 서")
    y -= 8 * mm
    c.setFont(font, 9)
    c.drawCentredString(w / 2, y, f"{ORG_NAME} {ORG_UNIT}")
    y -= 12 * mm

    c.setFont(font, 10)
    lines = [
        f"발주번호: {po.get('po_number','')}",
        f"거래처: {po.get('vendor_name','')}",
        f"요청일: {(po.get('requested_at') or '')[:16].replace('T',' ')}",
        f"상태: {po.get('status','')}",
    ]
    for ln in lines:
        c.drawString(20 * mm, y, ln)
        y -= 6 * mm
    y -= 4 * mm

    # 표 헤더
    c.setFont(font, 9)
    cols = [(20, "품목"), (95, "규격"), (120, "수량"), (140, "단가"), (170, "금액")]
    for x, label in cols:
        c.drawString(x * mm, y, label)
    y -= 2 * mm
    c.line(20 * mm, y, 195 * mm, y)
    y -= 6 * mm

    for it in items:
        c.drawString(20 * mm, y, str(it.get("item_name", ""))[:20])
        c.drawString(95 * mm, y, str(it.get("spec") or "")[:10])
        c.drawRightString(135 * mm, y, fmt_qty(it.get("qty")))
        c.drawRightString(165 * mm, y, f"{int(it.get('unit_price',0)):,}")
        c.drawRightString(195 * mm, y, f"{int(it.get('amount',0)):,}")
        y -= 6 * mm
        if y < 60 * mm:
            c.showPage(); y = h - 25 * mm; c.setFont(font, 9)

    y -= 2 * mm
    c.line(20 * mm, y, 195 * mm, y)
    y -= 8 * mm
    c.setFont(font, 11)
    c.drawRightString(195 * mm, y, f"합계  {fmt_won(po.get('total_amount', 0))}")
    y -= 16 * mm

    # 결재란 (R5)
    c.setFont(font, 9)
    req = _find_log(logs, ("REQUEST", "RESUBMIT"))
    apr = _find_log(logs, ("APPROVE",))
    if req:
        c.drawString(20 * mm, y,
                     f"요청   {req['position'] or ''} {req['user_name']}   "
                     f"{req['acted_at'][:16].replace('T',' ')}")
        y -= 7 * mm
    if apr:
        c.drawString(20 * mm, y,
                     f"결재   {apr['position'] or ''} {apr['user_name']}   "
                     f"{apr['acted_at'][:16].replace('T',' ')}   ✓ 승인")
    c.showPage()
    c.save()
    return buf.getvalue()


def _find_log(logs, actions):
    for lg in logs:
        if lg["action"] in actions:
            return lg
    return None
