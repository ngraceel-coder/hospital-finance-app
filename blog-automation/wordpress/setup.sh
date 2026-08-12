#!/bin/sh
# ============================================================
#  워드프레스 자동 세팅 스크립트 (wp-cli)
#  docker-compose 의 wpcli 서비스가 자동 실행한다.
#  - 코어 설치 / 관리자 생성 / 퍼머링크 / 언어(한국어)
#  - SEO·수익화 플러그인 설치
#  - 자동발행용 '애플리케이션 비밀번호' 생성 후 출력
# ============================================================
set -e

echo "⏳ 워드프레스 준비 대기..."
# DB + wp 파일이 준비될 때까지 대기
until wp core is-installed --allow-root >/dev/null 2>&1 || wp db check --allow-root >/dev/null 2>&1; do
  sleep 3
done

# 1) 코어 설치 (이미 설치돼 있으면 건너뜀)
if ! wp core is-installed --allow-root >/dev/null 2>&1; then
  echo "📦 워드프레스 코어 설치 중..."
  wp core install --allow-root \
    --url="$WP_URL" \
    --title="$WP_TITLE" \
    --admin_user="$WP_ADMIN_USER" \
    --admin_password="$WP_ADMIN_PASSWORD" \
    --admin_email="$WP_ADMIN_EMAIL" \
    --skip-email
else
  echo "✅ 이미 설치됨 - 설정만 갱신"
fi

# 2) 한국어
echo "🇰🇷 한국어 설정..."
wp language core install ko_KR --allow-root >/dev/null 2>&1 || true
wp site switch-language ko_KR --allow-root >/dev/null 2>&1 || true

# 3) 퍼머링크 = 글 이름 (SEO 필수)
echo "🔗 퍼머링크 설정..."
wp rewrite structure '/%postname%/' --allow-root
wp rewrite flush --allow-root

# 4) 불필요 기본 콘텐츠 정리
wp post delete 1 --force --allow-root >/dev/null 2>&1 || true   # Hello World
wp post delete 2 --force --allow-root >/dev/null 2>&1 || true   # Sample Page
wp plugin delete akismet hello --allow-root >/dev/null 2>&1 || true

# 5) SEO·수익화 플러그인 설치+활성화
echo "🔌 플러그인 설치 (SEO/사이트맵/수익화)..."
for p in wordpress-seo google-site-kit; do
  wp plugin install "$p" --activate --allow-root >/dev/null 2>&1 \
    && echo "   ✔ $p" || echo "   ⚠ $p 설치 실패(수동 설치 가능)"
done

# 6) 기본 카테고리 3종 (니치)
echo "🗂  카테고리 생성..."
for c in "정부지원금" "보험금융" "건강영양"; do
  wp term create category "$c" --allow-root >/dev/null 2>&1 || true
done

# 7) 자동발행용 애플리케이션 비밀번호 생성
echo "🔑 애플리케이션 비밀번호 생성..."
APP_PW=$(wp user application-password create "$WP_ADMIN_USER" "blog-automation" --porcelain --allow-root 2>/dev/null || true)

echo ""
echo "============================================================"
echo " ✅ 워드프레스 세팅 완료!"
echo "------------------------------------------------------------"
echo "  주소:        $WP_URL"
echo "  관리자:      $WP_URL/wp-admin  ($WP_ADMIN_USER)"
echo ""
echo "  ▼ 자동화 툴킷 ../.env 에 아래를 넣으세요:"
echo "    WP_URL=$WP_URL"
echo "    WP_USERNAME=$WP_ADMIN_USER"
echo "    WP_APP_PASSWORD=$APP_PW"
echo "============================================================"
