#!/usr/bin/env bash
# ============================================================
#  맥/리눅스 로컬 원클릭 실행기
#  워드프레스를 localhost:8080 에 띄우고 앱 비밀번호를 뽑아준다.
#
#  사용:  bash start-local.sh
# ============================================================
set -e
cd "$(dirname "$0")"

echo "🔍 도커 확인..."
if ! command -v docker >/dev/null 2>&1; then
  echo "❌ 도커가 없습니다. Docker Desktop 을 먼저 설치하세요:"
  echo "   https://www.docker.com/products/docker-desktop/"
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "❌ Docker Desktop 이 실행 중이 아닙니다. 앱을 켜고 다시 실행하세요."
  exit 1
fi

# .env 없으면 로컬 기본값으로 생성 (로컬 전용이라 기본 비번 OK)
if [ ! -f .env ]; then
  echo "📝 .env 생성 (로컬 기본값)..."
  cp .env.example .env
fi

echo "🚀 워드프레스 기동 중... (첫 실행은 이미지 다운로드로 2~5분)"
docker compose up -d

echo "⏳ 자동 세팅 대기..."
# wpcli 컨테이너가 세팅을 끝낼 때까지 로그를 기다린다
for i in $(seq 1 60); do
  if docker compose logs wpcli 2>/dev/null | grep -q "세팅 완료"; then
    break
  fi
  sleep 3
done

echo ""
echo "================= 세팅 결과 ================="
docker compose logs wpcli 2>/dev/null | tail -20
echo "============================================="
echo ""
echo "✅ 다음 단계:"
echo "  1) 브라우저에서 http://localhost:8080 열기"
echo "  2) 위 로그의 WP_APP_PASSWORD 를 ../.env 의 WP_APP_PASSWORD 에 붙여넣기"
echo "  3) cd .. && python3 run.py check   → 워드프레스 ✅ 확인"
