# 블로그 수익화 자동화 툴킷 🤖💰

Claude로 **주제 발굴 → 콘텐츠 생성 → 워드프레스 발행 → 수익화(애드센스·쿠팡)**를
자동으로 돌리는 파이프라인입니다.

> 📐 전체 구조 설계는 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md),
> 계정/도메인/키 준비는 [`docs/SETUP.md`](docs/SETUP.md) 를 보세요.

---

## 왜 이 조합인가 (한 줄 요약)

- **네이버 블로그**는 글쓰기 API가 폐지(2020)돼 완전 자동화가 불가하고 애드센스도 못 붙습니다.
- **워드프레스 + 애드센스 + 쿠팡파트너스**만이 "완전 무인 자동화 + 고수익"이 됩니다.
- 검색량 조사는 **네이버 검색광고 API**(무료)로 자동화합니다.

---

## 30초 구조

```
① keyword_research  네이버 검색광고 API로 검색량·경쟁도 → 수익성 점수
② topic_selector    Claude가 니치별 주제 5개 → 지표로 3개 확정
③ content_generator Claude가 SEO 최적화 본문/제목/메타/태그 생성
④ monetization      애드센스 광고 + 쿠팡 제휴링크 자동 삽입
⑤ wordpress_publisher  WP REST API로 발행/예약/카테고리·태그
⑥ scheduler         매일 자동 실행
```

## 확정 니치 3종 (순수 수익 최적화)

| 블로그 | 역할 | 수익 | 
|--------|------|------|
| 정부지원금·정책자금 안내 | 트래픽 엔진 | 애드센스 |
| 보험·금융 롱테일 정보 | 수익 엔진(최고 CPC) | 애드센스 |
| 건강·영양 + 제품추천 | 수익 다변화 | 애드센스 + 쿠팡 |

---

## 설치

```bash
cd blog-automation
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # 그리고 .env 에 API 키 입력
```

## 사용법

```bash
python run.py check       # 설정/자격증명 점검 (제일 먼저)
python run.py research     # 키워드 조사만 (네이버 API 필요)
python run.py topics       # 주제 5개→3개 선정 (발행 안 함)
python run.py generate     # 글 1개 생성 미리보기 (발행 안 함)
python run.py run          # 전체 파이프라인 실행
python run.py daily        # 하루치 자동 발행
```

### 매일 자동화 (cron)

```cron
# 매일 오전 9시 자동 발행
0 9 * * * cd /경로/blog-automation && /경로/.venv/bin/python scheduler/daily_run.py >> run.log 2>&1
```

또는 상주 프로세스:
```bash
python scheduler/daily_run.py --loop
```

---

## 안전하게 시작하기 (권장 순서)

1. `.env` 에서 **`DRY_RUN=true`** 유지 → `python run.py generate` 로 글 품질 확인
2. 워드프레스 연결되면 **`PUBLISH_STATUS=draft`** 로 초안 발행 → 사람이 검수
3. 품질 만족하면 `DRY_RUN=false`, `PUBLISH_STATUS=publish` 로 완전 자동화
4. `POSTS_PER_DAY` 는 3부터 시작 (초반 과다 발행은 저품질 페널티 위험)

> ⚠️ 금융·건강은 구글이 신뢰도(E-E-A-T)를 엄격 심사(YMYL)합니다.
> 초기에는 초안 검수를 거치는 걸 강력 권장합니다.

## 파일 구조

```
blog-automation/
├── run.py                  # 통합 CLI
├── config.py               # .env 설정 로더
├── .env.example            # API 키 템플릿
├── core/
│   ├── keyword_research.py  # ① 네이버 검색광고 API
│   ├── topic_selector.py    # ② 주제 선정 (Claude)
│   ├── content_generator.py # ③ 콘텐츠 생성 (Claude)
│   ├── monetization.py      # ④ 애드센스/쿠팡 삽입
│   ├── wordpress_publisher.py # ⑤ WP 발행
│   ├── llm.py               # Claude 공용 래퍼
│   └── pipeline.py          # 전체 오케스트레이션
├── scheduler/daily_run.py   # ⑥ 매일 자동 실행
└── docs/
    ├── ARCHITECTURE.md      # 구조 설계
    └── SETUP.md             # 계정/키 준비 가이드
```
