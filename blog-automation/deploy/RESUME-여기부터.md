# 📌 여기서 이어서 하기 (노트북 생기면)

> 폰으로 하다가 멈춘 지점. 서버는 이미 만들어졌고, 마지막 3개만 남았어요.

---

## ✅ 지금까지 완료 (건드리지 마세요, 다 됨)

- [x] AWS 계정 생성 + MFA 설정
- [x] Lightsail 인스턴스 생성 — **`Ubuntu-1`**, Ubuntu 22.04, **Seoul 리전**, $5 플랜
- [x] 고정 IP 붙임 → **`54.116.224.29`** ← 이게 내 서버 주소
- [x] SSH 접속용 계정: 사용자명 **`ubuntu`** (접속은 Lightsail "Connect using SSH" 브라우저 버튼)

> 💰 현재 비용: 서버 월 $5 (첫 몇 개월 무료 크레딧 있을 수 있음). 그 외 과금 없음.

---

## ⏳ 남은 3단계 (노트북 큰 화면에서, 약 15분)

### 1️⃣ 방화벽 443 포트 열기 (5초)
Lightsail → **`Ubuntu-1`** 클릭 → **Networking** 탭 → **IPv4 Firewall** →
**"+ Add rule"** → Application **HTTPS** 선택 → **Create**
- (노트북에선 Create 버튼이 바로 보임. 폰처럼 안 잘림)
- Source IP는 손대지 말 것 = 기본 "모두 허용"

### 2️⃣ 도메인 연결 (도메인: clearskysogood.net ✅ 구매완료)
- 도메인 산 사이트(OVH/Cloudflare 등)의 **DNS 관리**에서 **A 레코드** 설정:
  - `@`  (또는 clearskysogood.net)  →  `54.116.224.29`
  - `www`  →  `54.116.224.29`
- (전파 5분~1시간)
- ⚠️ Cloudflare에서 샀다면 A레코드 구름 아이콘을 **회색(DNS only)** 으로! (주황이면 Caddy SSL 충돌)

### 3️⃣ 서버 접속해서 한 줄 실행 → 블로그 완성
Lightsail → `Ubuntu-1` → **"Connect using SSH"**(브라우저 터미널) → 아래를 그대로 붙여넣기:
```bash
DOMAIN=clearskysogood.net ADMIN_EMAIL=ngraceel@gmail.com \
  bash <(curl -fsSL https://raw.githubusercontent.com/ngraceel-coder/hospital-finance-app/claude/blog-monetization-automation-84dfup/blog-automation/deploy/bootstrap-vps.sh)
```
→ 1~2분 뒤 **https://clearskysogood.net** 에 워드프레스 블로그 완성 + 앱 비밀번호 출력

### 4️⃣ (그다음) 자동화 가동
```bash
cd /opt/blog/blog-automation
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # ANTHROPIC_API_KEY, WP_APP_PASSWORD 입력
python3 run.py check
python3 run.py run       # 첫 자동 발행
```

---

## 내 정보 메모칸 (채워두면 편함)

- 서버 고정 IP: `54.116.224.29`
- 도메인: `clearskysogood.net` ✅
- 워드프레스 관리자 비번: `________________` (bootstrap 실행 시 출력됨)
- 앱 비밀번호(WP_APP_PASSWORD): `________________` (bootstrap 실행 시 출력됨)

---

**막히면 이 문서 위치 알려주고 "여기부터 이어서" 하면 됩니다.**
