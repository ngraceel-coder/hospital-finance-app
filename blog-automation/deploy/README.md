# 실서버 배포 (B) — 회원님이 할 일은 딱 3가지

나머지는 `bootstrap-vps.sh` 가 전부 자동으로 합니다.
(도커 설치 · 워드프레스 · 자동 HTTPS · 앱 비밀번호 생성)

---

## 회원님이 해야 하는 3가지 (제가 대신 못 하는 부분)

### 1️⃣ 서버 만들기 (약 5분, 월 $5~6)
아래 중 하나에서 계정 만들고 **가장 싼 인스턴스** 생성:

| 업체 | 추천 사양 | 월 요금 | 비고 |
|------|-----------|---------|------|
| **AWS Lightsail** | 1GB RAM / Ubuntu 22.04 | ~$5 | 가장 무난, 한국 리전 있음 |
| **Vultr** | 1GB RAM / Ubuntu 22.04 | ~$6 | 서울 리전, 빠름 |
| **DigitalOcean** | 1GB Droplet / Ubuntu | ~$6 | 문서 많음 |

> OS는 반드시 **Ubuntu 22.04 이상**. 생성 후 **서버 IP**와 **SSH 접속 정보**를 받습니다.

### 2️⃣ 도메인 준비 (약 5분, 연 1~2만원)
- 가비아 / Namecheap / Cloudflare 등에서 도메인 구매
- **DNS A 레코드**를 서버 IP로 지정:
  - `@`  →  서버IP
  - `www`  →  서버IP
- (전파에 5분~1시간)

### 3️⃣ 서버에 접속해서 한 줄 붙여넣기
SSH로 서버 접속 후:
```bash
DOMAIN=내도메인.com ADMIN_EMAIL=내이메일@gmail.com \
  bash <(curl -fsSL https://raw.githubusercontent.com/ngraceel-coder/hospital-finance-app/claude/blog-monetization-automation-84dfup/blog-automation/deploy/bootstrap-vps.sh)
```
→ 1~2분 뒤 **https://내도메인.com** 에 블로그 완성 + 앱 비밀번호 출력.

> ⚠️ SSL 자동발급은 도메인 DNS가 서버를 가리켜야 성공합니다. 2️⃣를 먼저 하세요.

---

## 그다음 (자동화 가동)

```bash
cd /opt/blog/blog-automation
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # ANTHROPIC_API_KEY, WP_APP_PASSWORD 등 입력
python3 run.py check       # 전부 ✅
python3 run.py run         # 첫 자동 발행
```

### 매일 자동 발행 (cron)
```bash
crontab -e
# 매일 오전 9시
0 9 * * * cd /opt/blog/blog-automation && ./.venv/bin/python scheduler/daily_run.py >> /opt/blog/run.log 2>&1
```

---

## 요약: 역할 분담

| 단계 | 누가 | 비용 |
|------|------|------|
| 서버 계정·인스턴스 생성 | **회원님** (카드 필요) | 월 $5~6 |
| 도메인 구매·DNS 연결 | **회원님** (카드 필요) | 연 1~2만원 |
| 도커·워드프레스·HTTPS·플러그인·앱비번 | 🤖 자동 스크립트 | 0 |
| 주제발굴·글생성·발행·수익화 | 🤖 자동화 툴킷 | Claude API 사용량 |

**회원님 순수 작업 시간 ≈ 15분. 나머지는 전부 자동.**
