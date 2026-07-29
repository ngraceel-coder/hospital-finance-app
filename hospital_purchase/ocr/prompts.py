"""거래처별 OCR 파싱 프롬프트 (계획서 6.3).

거래처마다 명세서 양식이 고정이므로 프롬프트를 따로 둘 수 있다.
vendors.memo 에 'PROMPT:' 로 시작하는 커스텀 지침이 있으면 그것을 덧붙인다.
"""

BASE_PROMPT = """당신은 병원 거래명세서(거래명세표) 이미지를 읽어 구조화하는 도구입니다.
아래 JSON 스키마로만 응답하세요. 설명·마크다운·코드펜스 없이 순수 JSON 만 출력합니다.

규칙:
- 읽을 수 없는 값은 추측하지 말고 null 로 둡니다.
- 숫자는 콤마·'원'·통화기호를 제거하고 정수로 만듭니다.
- 날짜는 YYYY-MM-DD 형식으로 정규화합니다.
- 품목별 lot_no(로트번호), expiry_date(유통기한)가 있으면 채우고 없으면 null.
- amount 는 qty * unit_price 와 대체로 일치해야 합니다.

스키마:
{
  "vendor_name": string|null,
  "invoice_no": string|null,
  "issue_date": "YYYY-MM-DD"|null,
  "items": [
    {"name": string, "spec": string|null, "qty": number,
     "unit_price": integer, "amount": integer,
     "lot_no": string|null, "expiry_date": "YYYY-MM-DD"|null}
  ],
  "supply_amount": integer|null,
  "tax_amount": integer|null,
  "total_amount": integer|null,
  "confidence": "high"|"medium"|"low"
}
"""


def build_prompt(vendor: dict = None) -> str:
    prompt = BASE_PROMPT
    if vendor and vendor.get("memo"):
        memo = vendor["memo"]
        if "PROMPT:" in memo:
            extra = memo.split("PROMPT:", 1)[1].strip()
            if extra:
                prompt += f"\n\n[이 거래처 특이사항]\n{extra}\n"
    return prompt
