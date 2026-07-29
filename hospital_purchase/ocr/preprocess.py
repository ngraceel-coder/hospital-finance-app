"""이미지 품질 게이트 · 보정 (계획서 6.2 / 6.1-③).

- 품질 검사: 해상도, 선명도(Laplacian variance), 문서 외곽 검출
- 보정: 외곽 검출 → 사다리꼴(원근) 보정 → 그림자 제거 → 대비 강화

cv2 미설치 환경에서도 앱이 죽지 않도록 모든 함수는 안전하게 실패한다.
"""
from config import MIN_SHORT_EDGE_PX, BLUR_LAPLACIAN_MIN

try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
except Exception:  # pragma: no cover
    _HAS_CV2 = False


def cv2_available() -> bool:
    return _HAS_CV2


def quality_check(image_path: str) -> dict:
    """품질 게이트. 반환: {ok, resolution_ok, sharp, blur_score, short_edge,
    doc_found, warnings:[...]}.

    cv2 없으면 검사를 건너뛰고 통과로 처리(경고 표기).
    """
    if not _HAS_CV2:
        return {"ok": True, "resolution_ok": True, "sharp": True,
                "blur_score": None, "short_edge": None, "doc_found": False,
                "warnings": ["OpenCV 미설치: 품질검사를 건너뜁니다."]}

    img = cv2.imread(image_path)
    if img is None:
        return {"ok": False, "resolution_ok": False, "sharp": False,
                "blur_score": 0, "short_edge": 0, "doc_found": False,
                "warnings": ["이미지를 열 수 없습니다."]}

    h, w = img.shape[:2]
    short_edge = min(h, w)
    resolution_ok = short_edge >= MIN_SHORT_EDGE_PX

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sharp = blur_score > BLUR_LAPLACIAN_MIN

    doc_found = _find_document_contour(img) is not None

    warnings = []
    if not resolution_ok:
        warnings.append(
            f"해상도 낮음(짧은 변 {short_edge}px < {MIN_SHORT_EDGE_PX}px). 재촬영 권장.")
    if not sharp:
        warnings.append(
            f"흐림 의심(선명도 {blur_score:.0f} < {BLUR_LAPLACIAN_MIN}). 재촬영 권장.")

    # 해상도 미달은 차단(ok=False), 흐림은 경고만
    return {"ok": resolution_ok, "resolution_ok": resolution_ok, "sharp": sharp,
            "blur_score": blur_score, "short_edge": short_edge,
            "doc_found": doc_found, "warnings": warnings}


def _find_document_contour(img):
    """가장 큰 사각형 컨투어(문서 외곽) 검출. 없으면 None."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(gray, 50, 150)
    edged = cv2.dilate(edged, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    img_area = img.shape[0] * img.shape[1]
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4 and cv2.contourArea(approx) > 0.25 * img_area:
            return approx.reshape(4, 2)
    return None


def _order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]      # top-left
    rect[2] = pts[np.argmax(s)]      # bottom-right
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]   # top-right
    rect[3] = pts[np.argmax(diff)]   # bottom-left
    return rect


def _four_point_transform(img, pts):
    rect = _order_points(pts.astype("float32"))
    (tl, tr, br, bl) = rect
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxW = int(max(widthA, widthB))
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxH = int(max(heightA, heightB))
    if maxW < 10 or maxH < 10:
        return img
    dst = np.array([[0, 0], [maxW - 1, 0], [maxW - 1, maxH - 1], [0, maxH - 1]],
                   dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(img, M, (maxW, maxH))


def _remove_shadow(img):
    """그림자 제거 + 대비 강화."""
    rgb_planes = cv2.split(img)
    result = []
    for plane in rgb_planes:
        dilated = cv2.dilate(plane, np.ones((7, 7), np.uint8))
        bg = cv2.medianBlur(dilated, 21)
        diff = 255 - cv2.absdiff(plane, bg)
        norm = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
        result.append(norm)
    return cv2.merge(result)


def enhance(image_path: str, out_path: str) -> str:
    """보정본을 out_path 로 저장하고 경로 반환.

    외곽 검출 실패 시 보정을 생략하고 원본을 그대로 저장(계획서 6.2).
    cv2 없으면 원본 경로를 그대로 반환.
    """
    if not _HAS_CV2:
        return image_path
    img = cv2.imread(image_path)
    if img is None:
        return image_path
    doc = _find_document_contour(img)
    if doc is not None:
        img = _four_point_transform(img, doc)
    try:
        img = _remove_shadow(img)
    except Exception:
        pass
    cv2.imwrite(out_path, img)
    return out_path
