"""
워드프레스 발행 코드 실동작 검증 (네트워크/실서버 불필요).

실제 워드프레스 REST API 응답을 흉내내는 목(mock) HTTP 서버를 띄우고,
WordPressPublisher 가 진짜 HTTP 요청으로 카테고리·태그·글을 만드는지 확인한다.

실행: python tests/test_publisher_mock.py
"""
import sys
import json
import base64
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# --- 가짜 워드프레스 REST API 서버 ---
STATE = {"categories": {}, "tags": {}, "posts": [], "next_id": 100, "auth_seen": []}


class MockWPHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 조용히
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def _auth_ok(self):
        h = self.headers.get("Authorization", "")
        STATE["auth_seen"].append(h)
        return h.startswith("Basic ")

    def do_GET(self):
        if not self._auth_ok():
            return self._send(401, {"code": "unauthorized"})
        if self.path.startswith("/wp-json/wp/v2/users/me"):
            return self._send(200, {"id": 1, "name": "admin"})
        if "/categories" in self.path:
            # search
            return self._send(200, list(STATE["categories"].values()))
        if "/tags" in self.path:
            return self._send(200, list(STATE["tags"].values()))
        return self._send(404, {"code": "not_found"})

    def do_POST(self):
        if not self._auth_ok():
            return self._send(401, {"code": "unauthorized"})
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or "{}")

        if self.path.endswith("/categories"):
            STATE["next_id"] += 1
            tid = STATE["next_id"]
            term = {"id": tid, "name": payload["name"]}
            STATE["categories"][tid] = term
            return self._send(201, term)
        if self.path.endswith("/tags"):
            STATE["next_id"] += 1
            tid = STATE["next_id"]
            term = {"id": tid, "name": payload["name"]}
            STATE["tags"][tid] = term
            return self._send(201, term)
        if self.path.endswith("/posts"):
            STATE["next_id"] += 1
            pid = STATE["next_id"]
            post = {
                "id": pid,
                "link": f"http://127.0.0.1/{payload.get('slug','post')}/",
                "status": payload.get("status", "draft"),
                "_payload": payload,
            }
            STATE["posts"].append(post)
            return self._send(201, post)
        return self._send(404, {"code": "not_found"})


def run():
    server = HTTPServer(("127.0.0.1", 8765), MockWPHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    # 환경변수로 목서버를 가리키게 하고 config 로드
    import os
    os.environ["WP_URL"] = "http://127.0.0.1:8765"
    os.environ["WP_USERNAME"] = "admin"
    os.environ["WP_APP_PASSWORD"] = "test test test test"
    os.environ["DRY_RUN"] = "false"

    import importlib
    import config as c
    importlib.reload(c)
    from core import wordpress_publisher as wp
    importlib.reload(wp)

    failures = []

    # 1) 연결/인증 테스트
    pub = wp.WordPressPublisher()
    assert pub.test_connection(), "연결 테스트 실패"
    print("✔ 인증 연결 성공")

    # 2) 글 발행 (카테고리+태그 자동 생성 포함)
    result = pub.publish(
        title="2025 근로장려금 신청 자격 총정리",
        html="<h2>개요</h2><p>내용</p>",
        category="정부지원금",
        tags=["근로장려금", "정부지원금", "신청방법"],
        meta_description="근로장려금 신청 자격 요약",
        slug="geunro-jangryeogeum",
        status="publish",
    )
    print(f"✔ 글 발행: id={result['id']} status={result['status']}")
    print(f"  link={result['link']}")

    # 검증
    if not result["id"]:
        failures.append("글 id 없음")
    if result["status"] != "publish":
        failures.append(f"status 불일치: {result['status']}")
    if len(STATE["categories"]) != 1:
        failures.append(f"카테고리 생성 오류: {len(STATE['categories'])}")
    if len(STATE["tags"]) != 3:
        failures.append(f"태그 생성 오류: {len(STATE['tags'])}개 (기대 3)")
    posted = STATE["posts"][0]["_payload"]
    if "categories" not in posted or "tags" not in posted:
        failures.append("글에 카테고리/태그 연결 누락")
    if not any(a.startswith("Basic ") for a in STATE["auth_seen"]):
        failures.append("인증 헤더 미전송")

    # 3) DRY_RUN 모드도 확인
    os.environ["DRY_RUN"] = "true"
    importlib.reload(c)
    importlib.reload(wp)
    dry = wp.publish_article(
        {"title": "테스트", "html": "<p>x</p>", "slug": "t",
         "tags": [], "category": "", "meta_description": ""}
    )
    if not dry.get("dry_run"):
        failures.append("DRY_RUN 모드 동작 안 함")
    else:
        print(f"✔ DRY_RUN 모드: 로컬 저장 → {Path(dry['saved']).name}")

    server.shutdown()

    print("\n" + "=" * 50)
    if failures:
        print("❌ 실패:")
        for f in failures:
            print("   -", f)
        sys.exit(1)
    print("✅ 전체 통과 — 발행 코드가 실제 WP REST API 흐름에서 정상 동작")
    print(f"   생성된 카테고리 {len(STATE['categories'])}개, "
          f"태그 {len(STATE['tags'])}개, 글 {len(STATE['posts'])}개")


if __name__ == "__main__":
    run()
