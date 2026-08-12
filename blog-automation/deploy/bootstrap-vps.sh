#!/usr/bin/env bash
# ============================================================
#  VPS 원클릭 부트스트랩 (Ubuntu 22.04+ / Debian)
#
#  새로 만든 서버에 root 로 접속해서 이것 하나만 실행하면:
#   - 도커 설치
#   - 이 저장소 clone
#   - 강력한 비밀번호 자동 생성
#   - 워드프레스 + 자동 HTTPS(Caddy) 기동
#   - 자동발행용 앱 비밀번호 출력
#
#  실행 예:
#    DOMAIN=myblog.com ADMIN_EMAIL=you@gmail.com bash bootstrap-vps.sh
#
#  (DOMAIN/ADMIN_EMAIL 안 주면 물어봄)
# ============================================================
set -e

REPO_URL="${REPO_URL:-https://github.com/ngraceel-coder/hospital-finance-app.git}"
BRANCH="${BRANCH:-claude/blog-monetization-automation-84dfup}"
INSTALL_DIR="${INSTALL_DIR:-/opt/blog}"

# ---- 입력 확인 ----
if [ -z "$DOMAIN" ]; then
  printf "블로그 도메인 (예: myblog.com): "; read DOMAIN
fi
if [ -z "$ADMIN_EMAIL" ]; then
  printf "관리자 이메일: "; read ADMIN_EMAIL
fi
if [ -z "$DOMAIN" ] || [ -z "$ADMIN_EMAIL" ]; then
  echo "❌ DOMAIN 과 ADMIN_EMAIL 은 필수입니다."; exit 1
fi

echo "▶ 도메인: $DOMAIN / 이메일: $ADMIN_EMAIL"

# ---- 1. 필수 패키지 + 도커 ----
if ! command -v docker >/dev/null 2>&1; then
  echo "📦 도커 설치 중..."
  curl -fsSL https://get.docker.com | sh
fi
if ! command -v git >/dev/null 2>&1; then
  apt-get update -y && apt-get install -y git
fi

# ---- 2. 저장소 clone ----
if [ ! -d "$INSTALL_DIR/.git" ]; then
  echo "⬇️  저장소 clone..."
  git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
else
  echo "🔄 저장소 업데이트..."
  git -C "$INSTALL_DIR" pull --ff-only || true
fi

cd "$INSTALL_DIR/blog-automation/wordpress"

# ---- 3. .env 생성 (강력한 랜덤 비밀번호) ----
rand() { openssl rand -base64 18 | tr -d '/+=' | cut -c1-20; }
if [ ! -f .env ]; then
  echo "🔐 비밀번호 자동 생성..."
  ADMIN_PW=$(rand)
  cat > .env <<EOF
DOMAIN=$DOMAIN
WP_TITLE=내 수익형 블로그
WP_ADMIN_USER=admin
WP_ADMIN_PASSWORD=$ADMIN_PW
WP_ADMIN_EMAIL=$ADMIN_EMAIL
WP_DB_NAME=wordpress
WP_DB_USER=wpuser
WP_DB_PASSWORD=$(rand)
WP_DB_ROOT_PASSWORD=$(rand)
EOF
  echo "   관리자 비밀번호: $ADMIN_PW   (안전한 곳에 보관!)"
fi

# ---- 4. 기동 ----
echo "🚀 워드프레스 + HTTPS 기동... (SSL 발급까지 1~2분)"
docker compose -f docker-compose.prod.yml up -d

# ---- 5. 세팅 완료 대기 & 앱 비밀번호 ----
echo "⏳ 자동 세팅 대기..."
for i in $(seq 1 60); do
  if docker compose -f docker-compose.prod.yml logs wpcli 2>/dev/null | grep -q "세팅 완료"; then
    break
  fi
  sleep 3
done

echo ""
echo "================= 결과 ================="
docker compose -f docker-compose.prod.yml logs wpcli 2>/dev/null | tail -18
echo "========================================"
echo ""
echo "✅ 배포 완료!"
echo "  블로그:   https://$DOMAIN"
echo "  관리자:   https://$DOMAIN/wp-admin"
echo ""
echo "다음: 위 로그의 WP_APP_PASSWORD 를 자동화 툴킷 .env 에 넣고"
echo "      cd $INSTALL_DIR/blog-automation && python3 run.py check"
