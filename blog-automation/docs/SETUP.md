# 셋업 가이드 — 계정·도메인·API 키 준비

이 문서대로 준비하면 자동화가 실제로 돌아갑니다. 순서대로 진행하세요.

---

## 0. 준비물 요약

| 항목 | 용도 | 비용 | 필수 |
|------|------|------|------|
| Anthropic API 키 | Claude 콘텐츠 생성 | 사용량 과금 | ✅ |
| 네이버 검색광고 계정 | 키워드 검색량 조회 | 무료(광고비 X) | ✅ |
| 도메인 | 블로그 주소 | 연 1~2만원 | ✅ |
| 워드프레스 호스팅 | 블로그 운영 | 월 0~1.5만원 | ✅ |
| 구글 애드센스 | 광고 수익 | 무료(승인 필요) | ✅ |
| 쿠팡 파트너스 | 제휴 수익 | 무료(승인 필요) | 선택 |

---

## 1. Anthropic API 키 (Claude)

1. https://console.anthropic.com 가입
2. **API Keys → Create Key** → 키 복사
3. `.env` 에 `ANTHROPIC_API_KEY=sk-ant-...` 입력
4. 결제 수단 등록(사용량 과금). 글 1편당 대략 수백~수천 토큰 수준.

---

## 2. 네이버 검색광고 API (검색량 조사) — 무료

> 광고를 실제로 집행하지 않아도 API 호출은 무료입니다.

1. https://searchad.naver.com 접속 → **신규 광고주 가입**
2. 로그인 후 우측 상단 **도구 → API 사용 관리**
3. **네이버 검색광고 API 라이선스** 발급 → 아래 3가지 확인
   - `액세스 라이선스` → `.env` 의 `NAVER_AD_API_KEY`
   - `비밀키` → `NAVER_AD_SECRET_KEY`
   - `CUSTOMER ID`(내 정보에 표시) → `NAVER_AD_CUSTOMER_ID`
4. 확인: `python run.py research`

---

## 3. 도메인 + 워드프레스 호스팅

### 옵션 A — 가장 쉬움 (관리형)
- **Bluehost / Cloudways / 카페24 워드프레스** 등에서 원클릭 설치
- 도메인 포함 상품 선택하면 세팅 간단

### 옵션 B — 저렴/유연 (직접)
- 도메인: 가비아/후이즈/Namecheap
- 호스팅: DigitalOcean/Vultr($6~)에 워드프레스 이미지 설치, 또는 카페24 웹호스팅

### 워드프레스 설치 후 필수 설정
1. **고유주소(Permalink)** → '글 이름' 방식으로 변경 (SEO)
2. 플러그인 설치:
   - **Rank Math SEO** 또는 Yoast SEO (메타·사이트맵)
   - **Google Site Kit** (애드센스·애널리틱스 연동)
3. **애플리케이션 비밀번호 발급** (자동 발행용):
   - 관리자 → 사용자 → 프로필 → 맨 아래 **애플리케이션 비밀번호**
   - 이름 입력 후 생성 → 나온 비밀번호를 `.env` `WP_APP_PASSWORD` 에 입력
   - `WP_URL`(예: https://myblog.com), `WP_USERNAME`(로그인 아이디)도 입력
4. 확인: `python core/wordpress_publisher.py`

---

## 4. 구글 애드센스 (광고 수익)

1. 블로그에 **글 20~30개 이상** 쌓은 뒤 신청 (빈 사이트는 거절됨)
2. https://adsense.google.com → 사이트 추가 → 심사(수일~수주)
3. 승인 후 **광고 단위 만들기 → 인아티클 광고** 생성
   - 게시자 ID `ca-pub-...` → `.env` `ADSENSE_CLIENT_ID`
   - 광고 슬롯 ID(숫자) → `ADSENSE_SLOT_ID`
4. `<head>` 로더는 Google Site Kit이 자동 삽입하거나,
   `core/monetization.py` 의 `adsense_header_script()` 를 테마 헤더에 1회 삽입

> 애드센스 승인 전까지는 글만 자동 생성해 쌓아두세요(`PUBLISH_STATUS=publish`).

---

## 5. 쿠팡 파트너스 (제휴 수익) — 선택

1. https://partners.coupang.com 가입 → 심사
2. 승인 후 **트래킹 코드** 확인 → `.env` `COUPANG_PARTNERS_TAG`
3. 건강·생활 니치 글에 자동으로 제휴 박스가 삽입됩니다.
4. ⚠️ 글에 "쿠팡 파트너스 활동으로 수수료를 받습니다" 문구 필수 (툴이 자동 삽입).

---

## 6. 첫 실행 체크리스트

```bash
python run.py check      # 전부 ✅ 인지 확인
python run.py topics     # 주제 3개 확정 확인
python run.py generate   # 샘플 글 품질 확인 (data/output/ 에 저장)
# 만족하면 .env 에서 DRY_RUN=false
python run.py run        # 실제 발행
```

---

## 자주 묻는 질문

**Q. 네이버 API 없이도 되나요?**
→ 됩니다. 없으면 Claude가 일반 수요 지식으로 주제를 추정합니다(정확도↓). 검색량 검증을 위해 발급 권장.

**Q. 저품질/스팸 페널티가 걱정됩니다.**
→ 초기 `PUBLISH_STATUS=draft` 로 사람이 검수, 하루 3개 이하, 정보성·독창성 유지가 핵심입니다. 순수 복붙/양산형은 구글 헬프풀 콘텐츠 업데이트에서 불리합니다.

**Q. 수익은 언제부터?**
→ 신규 도메인은 구글 샌드박스(3~6개월) 후 트래픽이 붙습니다. 이 기간에 글 자산을 쌓는 게 이 자동화의 목적입니다.
