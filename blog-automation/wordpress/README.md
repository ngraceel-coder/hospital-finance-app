# 워드프레스 원클릭 배포 패키지

명령어 하나로 **자동발행 준비가 끝난** 워드프레스 블로그를 띄웁니다.
(코어 설치 + 한국어 + 퍼머링크 + SEO 플러그인 + 카테고리 + **앱 비밀번호 자동 생성**)

---

## A. 지금 내 PC에서 테스트로 띄우기 (무료)

도커만 있으면 됩니다.

```bash
cd blog-automation/wordpress
cp .env.example .env          # 비밀번호들 바꾸기
docker compose up -d
# 30초~1분 후 자동세팅 로그 확인:
docker compose logs wpcli
```

- 브라우저에서 **http://localhost:8080** → 블로그 확인
- 로그 맨 아래 출력된 **WP_APP_PASSWORD** 를 복사해서
  상위 폴더의 `../.env` (자동화 툴킷)에 붙여넣기:
  ```
  WP_URL=http://localhost:8080
  WP_USERNAME=admin
  WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
  ```
- 이제 `cd .. && python run.py check` → 워드프레스 ✅ 확인 후 `python run.py run`

> 로컬은 인터넷에 공개되지 않습니다(내 컴퓨터에서만 보임). 파이프라인 검증·연습용.

---

## B. 실제 공개 블로그로 띄우기 (수익화 가능)

### 1) 서버 준비 (둘 중 하나)
- **VPS**: DigitalOcean/Vultr/라이트세일 ($5~6/월) — Ubuntu 선택
- **국내**: 카페24/가비아 클라우드

### 2) 서버에서 도커 설치 후 위와 동일하게 실행
```bash
# Ubuntu 기준
curl -fsSL https://get.docker.com | sh
git clone <이 저장소>   # 또는 wordpress 폴더만 복사
cd blog-automation/wordpress
cp .env.example .env
# .env 에서 WP_URL=https://내도메인.com 으로, 비밀번호 강력하게
docker compose up -d
```

### 3) 도메인 + HTTPS 연결
- 도메인(가비아 등)의 A레코드를 **서버 IP**로 지정
- HTTPS: 앞단에 **Caddy** 또는 **Nginx + Let's Encrypt** 리버스프록시
  (가장 쉬운 건 Caddy 한 줄 설정 — 자동 SSL)

<details>
<summary>Caddy 자동 HTTPS 예시 (Caddyfile)</summary>

```
your-domain.com {
    reverse_proxy localhost:8080
}
```
</details>

### 4) 애드센스/쿠팡
- 글 20~30개 쌓은 뒤 애드센스 신청 (`docs/SETUP.md` 참고)
- 자동화 툴킷 `../.env` 에 `ADSENSE_*`, `COUPANG_PARTNERS_TAG` 입력

---

## 관리 명령

```bash
docker compose ps                 # 상태
docker compose logs -f wordpress  # 로그
docker compose down               # 중지 (데이터 유지)
docker compose down -v            # 완전 삭제 (데이터까지) ⚠️
```

## 백업
```bash
# DB 백업
docker compose exec db mariadb-dump -u root -p wordpress > backup.sql
# 업로드 파일은 wp_data 볼륨에 있음
```

## 왜 도커인가
- 어느 서버든 동일하게 뜸(환경 차이 없음), 삭제·재생성 쉬움
- 관리형 호스팅(카페24 등)을 써도 되지만, 그건 REST API/앱비밀번호 설정을
  직접 해야 하고 자동화 제약이 있을 수 있어 **도커 자가호스팅을 권장**합니다.
