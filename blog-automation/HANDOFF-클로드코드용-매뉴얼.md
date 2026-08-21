# 🤝 인수인계 매뉴얼 — Claude Code에게

> **이 문서를 읽는 너는 Claude Code다.** 사용자(남편분)를 도와 이 블로그 수익 자동화
> 시스템을 처음부터 구축하는 것이 네 임무다. 이 시스템은 이미 한 번 성공적으로
> 구축·운영되고 있다 (clearskysogood.net — 아내분의 블로그). 너는 같은 코드로
> **사용자 본인의 새 블로그**를 만들면 된다. 검증된 길이니 이 문서 순서대로 가라.

---

## 이 시스템이 뭔가

**완전 자동 블로그 수익화 파이프라인.** 매일 정해진 시각에 서버가 혼자서:
```
주제 발굴(시즌 키워드 포함) → Claude API로 SEO 글 작성(후킹 프롬프트)
→ 카드형 썸네일 생성 → 내부링크 연결 → 워드프레스에 자동 발행
→ (애드센스 승인 후) 광고 자동 삽입 = 수익
```
- 운영비: 서버 $5/월 + 도메인 ~$12/년 + Claude API $10~20/월 ≈ **월 3~4만원**
- 수익 목표: 6개월 차에 월 10만원+ (애드센스 RPM 기준 하루 300~1,000뷰 필요)
- 신규 도메인은 구글 샌드박스로 **첫 2~3개월 조회수 0이 정상**. 그 기간이 글 자산 축적기다.

## 코드 구조 (전부 이 폴더에 있음)

```
blog-automation/
├── run.py                  # 통합 CLI: check/research/topics/generate/run/daily
├── config.py               # .env 로더
├── .env.example            # 키 템플릿 → 복사해서 .env 만들기
├── core/
│   ├── keyword_research.py  # 네이버 검색광고 API 검색량 조사(선택)
│   ├── topic_selector.py    # 니치 5종 → 주제 후보 → 상위 3개 확정
│   ├── content_generator.py # 후킹 프롬프트로 글 생성(+슬러그/FAQ스키마/내부링크)
│   ├── images.py            # 카드형 썸네일 생성 + Pexels 스톡사진(선택)
│   ├── monetization.py      # 애드센스/쿠팡 코드 삽입
│   ├── wordpress_publisher.py # WP REST API 발행(+미디어 업로드)
│   └── pipeline.py          # 전체 오케스트레이션
├── scheduler/daily_run.py   # 매일 자동 실행
├── wordpress/               # 워드프레스 원클릭 배포 (docker-compose.prod.yml,
│   │                        #   setup.sh, apply-design.sh, design.css)
├── deploy/bootstrap-vps.sh  # 새 서버 한 줄 셋업 스크립트
├── deploy/README.md         # 서버/도메인 준비 가이드
└── docs/ARCHITECTURE.md, SETUP.md  # 설계·계정 준비 상세
```

## ⚠️ 시작 전 사용자에게 확인할 것 (Claude Code야, 먼저 물어봐라)

1. **새 블로그를 만들 것인가?** (기본 가정: 그렇다. 아내분의 서버/도메인/계정을 재사용하지 말 것 —
   수익 정산 계정이 분리되어야 하고, 한 서버에 얹으면 장애가 같이 난다)
2. **니치(주제군)를 뭘로 할 것인가?** 기본 5종(정부지원금/보험금융/부동산정책/건강영양/생활리뷰)을
   그대로 써도 되고, `core/keyword_research.py`의 `NICHE_SEEDS`와 `core/pipeline.py`의 `NICHES`를
   바꿔 다른 니치로 가도 된다. **아내분 블로그와 니치를 다르게 하면 서로 경쟁하지 않아 더 좋다.**
3. **블로그 이름/도메인 아이디어** — 도메인 구매 전에 정해야 한다.

## 구축 순서 (사용자가 해야 하는 것 vs 네가 하는 것)

### 1단계 — 사용자 계정 준비 (사람만 가능, 총 ~30분)
너는 각 단계에서 화면을 안내해라. 상세는 `docs/SETUP.md`, `deploy/README.md` 참고.

| 순서 | 할 일 | 비용 | 비고 |
|---|---|---|---|
| ① | Anthropic API 키 발급 (console.anthropic.com) | 사용량 과금 | 필수 |
| ② | AWS Lightsail 가입 → **Ubuntu 22.04, 1GB, 서울** 인스턴스 | 월 $5 | ⚠️ Blueprint는 "OS Only"! WordPress 앱 이미지 금지 |
| ③ | 고정 IP 붙이기 + 방화벽에 **HTTPS(443)** 추가 | - | 인스턴스→Networking 탭 |
| ④ | 도메인 구매 (Cloudflare/Namecheap) + A레코드 `@`,`www` → 고정IP | 연 ~$12 | Cloudflare면 구름 아이콘 **회색(DNS only)** 필수! |
| ⑤ | (선택·추천) 네이버 검색광고 광고주 가입 → 도구→API 사용관리에서 키 3종 | 무료 | 실검색량 기반 주제 선정 가능해짐 |
| ⑥ | (선택) Pexels API 키 (pexels.com/api) | 무료 | 본문 스톡사진 |

### 2단계 — 서버 셋업 (Lightsail 브라우저 SSH에서 한 줄)
```bash
DOMAIN=사용자도메인.com ADMIN_EMAIL=사용자이메일 \
  bash <(curl -fsSL https://raw.githubusercontent.com/<이코드가있는저장소>/<브랜치>/blog-automation/deploy/bootstrap-vps.sh)
```
- ⚠️ 저장소 URL은 이 코드를 올려둔 곳으로 바꿔라 (사용자의 GitHub에 새 저장소로 올리는 것 권장 —
  `bootstrap-vps.sh` 상단의 `REPO_URL`/`BRANCH` 기본값도 그에 맞게 수정할 것)
- 출력되는 **관리자 비밀번호**와 **WP_APP_PASSWORD를 반드시 메모**시켜라
- 완료되면 https://도메인 에 워드프레스가 떠 있어야 한다
- 이 스크립트가 하는 일: 도커 설치→코드 clone(~/blog)→워드프레스+MariaDB+Caddy(자동 HTTPS)
  →한국어/퍼머링크/SEO플러그인/카테고리/앱비밀번호 자동 세팅

### 3단계 — 자동화 연결 (서버에서)
```bash
sudo apt-get install -y fonts-nanum unzip   # 썸네일용 한글 폰트
cd ~/blog/blog-automation
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
`.env`에 채울 것: `ANTHROPIC_API_KEY`, `WP_URL=https://도메인`, `WP_USERNAME=admin`,
`WP_APP_PASSWORD=(2단계 메모)`, `DRY_RUN=false`, `PUBLISH_STATUS=publish`
(+ 선택: `NAVER_AD_*` 3종, `PEXELS_API_KEY`)

```bash
python3 run.py check     # 전부 ✅ 확인
python3 run.py run       # 첫 발행 (글 3개가 실제로 올라간다)
```

### 4단계 — 디자인 + 매일 자동화
```bash
bash ~/blog/blog-automation/wordpress/apply-design.sh   # 테마+브랜드CSS
# Astra 다운로드 실패 시(가끔 있음) 수동 우회:
#   cd /tmp && curl -L -o astra.zip https://downloads.wordpress.org/theme/astra.zip && rm -rf astra && unzip -oq astra.zip
#   sudo docker cp /tmp/astra wordpress-wordpress-1:/var/www/html/wp-content/themes/
#   sudo docker exec wordpress-wordpress-1 chown -R www-data:www-data /var/www/html/wp-content/themes/astra
#   bash ~/blog/blog-automation/wordpress/apply-design.sh
```
```bash
# 매일 자동 발행 (UTC 9시 = 한국 저녁 6시)
(crontab -l 2>/dev/null; echo '0 9 * * * cd /home/ubuntu/blog/blog-automation && ./.venv/bin/python run.py daily >> /home/ubuntu/blog/run.log 2>&1') | crontab -
```
- 디자인 색은 `wordpress/design.css` 수정 → 스크립트 재실행 (사용자 취향대로 바꿔줘라)
- wp-admin에서 사이트 제목/닉네임 설정 안내 (설정→일반, 사용자→프로필)

### 5단계 — SEO 등록 + 수익화 (사용자 계정 필요)
1. 구글 서치콘솔 등록 + `sitemap_index.xml` 제출 (도메인 소유 확인은 DNS TXT)
2. 네이버 서치어드바이저 등록
3. **글 20~30개 쌓인 뒤(약 열흘)** 애드센스 신청 → 승인되면 `.env`에
   `ADSENSE_CLIENT_ID`/`ADSENSE_SLOT_ID` 입력 → 이후 발행 글에 광고 자동 삽입
4. (선택) 쿠팡 파트너스 가입 → `COUPANG_PARTNERS_TAG` 입력

## 이미 밟은 함정들 (같은 데서 넘어지지 마라)

| 함정 | 해결 |
|---|---|
| Lightsail에서 Database/WordPress앱을 잘못 생성 | Instance + "OS Only" Ubuntu만 |
| 모바일 브라우저에서 방화벽 팝업 버튼 잘림 | PC 브라우저 또는 데스크톱 모드 |
| bootstrap이 `/opt/blog` 권한 에러 | 이미 수정됨(~/blog에 설치). 구버전 쓰지 말 것 |
| MariaDB unhealthy (1GB RAM + 초기화 중단) | 스왑 2G 추가 + db 볼륨 삭제 후 재기동 (RESUME 문서 참고) |
| `temperature` 파라미터로 Claude API 400 | 이미 수정됨. 최신 모델은 샘플링 파라미터 금지 |
| `crontab -e`/nano가 브라우저 SSH에서 먹통 | 비대화식 명령 사용 (위 cron 한 줄처럼) |
| 재접속하면 홈 폴더에서 시작 | 항상 `cd ~/blog/blog-automation && source .venv/bin/activate` 먼저 |
| Cloudflare 주황 구름(Proxied) | 회색(DNS only)으로 — 아니면 Caddy SSL 발급 실패 |

## 운영 명령 치트시트

```bash
python3 run.py check      # 설정 점검
python3 run.py topics     # 주제만 뽑아보기(발행 안 함)
python3 run.py run        # 즉시 3개 발행
cat ~/blog/run.log        # cron 발행 로그
grep WP_ADMIN_PASSWORD ~/blog/blog-automation/wordpress/.env   # 관리자 비번 분실 시
cd ~/blog/blog-automation/wordpress && sudo docker compose -f docker-compose.prod.yml ps   # 컨테이너 상태
```

## 마지막 당부

- 프롬프트(글맛)는 `core/content_generator.py`의 `CONTENT_SYSTEM`에 있다. 사용자가 "글이 어색하다"고
  하면 거기를 튜닝해라. 후킹 3단 도입부·AI 상투어 금지 규칙은 유지할 것.
- 발행량은 `.env`의 `POSTS_PER_DAY`. 초반 과다 발행(10개+/일)은 저품질 위험 — 3개가 적정.
- 뭐든 막히면: 에러 전문을 읽고, 이 폴더의 docs/를 찾아보고, 그래도 모르면 사용자에게
  화면/로그를 요청해라. 이 시스템은 한 번 끝까지 완주된 검증된 코드다. 화이팅. 🚀
