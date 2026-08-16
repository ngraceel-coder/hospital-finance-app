#!/usr/bin/env bash
# ============================================================
#  디자인 원클릭 적용
#  - Astra 테마 설치·활성화 (가볍고 애드센스 친화적)
#  - design.css 를 사용자 정의 CSS로 주입 (맑은 하늘 브랜드)
#
#  사용 (서버에서):  bash ~/blog/blog-automation/wordpress/apply-design.sh
# ============================================================
set -e
cd "$(dirname "$0")"

DC="sudo docker compose -f docker-compose.prod.yml"

echo "🎨 테마 설치 + 브랜드 CSS 적용 중..."
$DC run --rm --entrypoint bash wpcli -c '
set -e
# 1) Astra 테마 설치 (에러 표시, 실패 시 --force 재시도, 그래도 안 되면 내장 테마 폴백)
THEME=astra
if ! wp theme is-installed astra --allow-root; then
  wp theme install astra --allow-root \
    || wp theme install astra --force --allow-root \
    || true
fi
if wp theme is-installed astra --allow-root; then
  wp theme activate astra --allow-root
else
  echo "[i] Astra 설치 실패 → 내장 테마로 대체 적용"
  # 워드프레스에 기본 포함된 최신 테마 찾기
  THEME=$(wp theme list --field=name --allow-root | grep -E "^twenty" | sort -r | head -1)
  wp theme activate "$THEME" --allow-root
fi
echo "[i] 활성 테마: $THEME"

# 2) design.css 를 사용자 정의 CSS(post_type=custom_css)로 주입
CSS_FILE=/design.css
if [ ! -f "$CSS_FILE" ]; then
  echo "design.css 마운트 안 됨 — docker-compose.prod.yml 볼륨 확인"; exit 1
fi
POST_ID=$(wp post list --post_type=custom_css --title="$THEME" --field=ID --allow-root | head -1)
if [ -z "$POST_ID" ]; then
  POST_ID=$(wp post create --post_type=custom_css --post_status=publish \
    --post_title="$THEME" --post_content="$(cat $CSS_FILE)" --porcelain --allow-root)
else
  wp post update "$POST_ID" --post_content="$(cat $CSS_FILE)" --allow-root >/dev/null
fi
wp theme mod set custom_css_post_id "$POST_ID" --allow-root

# 3) 마무리
wp cache flush --allow-root 2>/dev/null || true
echo ""
echo "✅ 디자인 적용 완료! (테마: $THEME) 브라우저에서 새로고침(Ctrl+Shift+R) 해보세요."
'
