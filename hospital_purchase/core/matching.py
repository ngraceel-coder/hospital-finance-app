"""품목명 매칭 · 별칭 학습 (계획서 6.4).

1. item_aliases 완전 일치 → MATCHED
2. items(name+spec) 유사도(rapidfuzz)
     >= MATCH_STRONG 단독 → MATCHED
     MATCH_WEAK ~ MATCH_STRONG → AMBIGUOUS (후보 제시)
     < MATCH_WEAK → UNMATCHED
3. 사람이 확정하면 add_alias 로 학습 → 다음부터 1번에서 걸림.
"""
from db.queries import find_alias, add_alias, get_item, list_items
from config import MATCH_STRONG, MATCH_WEAK


def _score(a: str, b: str) -> float:
    from rapidfuzz import fuzz

    if not a or not b:
        return 0.0
    return float(fuzz.token_sort_ratio(a, b))


def _item_label(item: dict) -> str:
    spec = item.get("spec") or ""
    return f"{item['name']} {spec}".strip()


def match_item(ocr_name, vendor_id=None, candidates=None):
    """OCR 품목명 → 매칭 결과.

    반환: {
      status: MATCHED/AMBIGUOUS/UNMATCHED,
      item_id: int|None,
      candidates: [{item_id, label, score}]  (상위 3개)
    }
    """
    ocr_name = (ocr_name or "").strip()
    # 1) 별칭 완전 일치
    alias_item = find_alias(ocr_name, vendor_id)
    if alias_item:
        it = get_item(alias_item)
        if it and it["is_active"]:
            return {"status": "MATCHED", "item_id": alias_item,
                    "candidates": [{"item_id": alias_item,
                                    "label": _item_label(it), "score": 100.0}]}

    # 2) 유사도
    pool = candidates if candidates is not None else list_items(active_only=True)
    scored = []
    for it in pool:
        s = _score(ocr_name, _item_label(it))
        scored.append({"item_id": it["id"], "label": _item_label(it), "score": s})
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:3]

    if not top:
        return {"status": "UNMATCHED", "item_id": None, "candidates": []}

    best = top[0]
    second = top[1]["score"] if len(top) > 1 else 0.0
    if best["score"] >= MATCH_STRONG and best["score"] - second >= 1:
        return {"status": "MATCHED", "item_id": best["item_id"], "candidates": top}
    if best["score"] >= MATCH_WEAK:
        return {"status": "AMBIGUOUS", "item_id": None, "candidates": top}
    return {"status": "UNMATCHED", "item_id": None, "candidates": top}


def learn(ocr_name, item_id, vendor_id=None):
    """확정 시 별칭 저장(학습)."""
    if ocr_name and item_id:
        add_alias(item_id, ocr_name, vendor_id)
