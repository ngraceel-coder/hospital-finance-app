"""
워드프레스 자동 발행 엔진 - WP REST API.

워드프레스 관리자 → 사용자 → 프로필 → '애플리케이션 비밀번호' 발급 후 사용.
카테고리/태그를 자동 생성(없으면)하고 글을 발행/예약/초안 저장한다.

REST API 문서: https://developer.wordpress.org/rest-api/reference/posts/
"""
from __future__ import annotations
import base64
from typing import Optional

import requests

from config import config


class WordPressPublisher:
    def __init__(self):
        self.base = f"{config.wp_url}/wp-json/wp/v2"
        token = base64.b64encode(
            f"{config.wp_username}:{config.wp_app_password}".encode()
        ).decode()
        self.headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }
        self.session = requests.Session()

    # ---------- 카테고리/태그 관리 ----------
    def _get_or_create_term(self, taxonomy: str, name: str) -> Optional[int]:
        """taxonomy = 'categories' | 'tags'. 이름으로 찾고 없으면 생성 후 id 반환."""
        if not name:
            return None
        # 검색
        r = self.session.get(
            f"{self.base}/{taxonomy}",
            params={"search": name},
            headers=self.headers,
            timeout=15,
        )
        r.raise_for_status()
        for term in r.json():
            if term["name"] == name:
                return term["id"]
        # 생성
        r = self.session.post(
            f"{self.base}/{taxonomy}",
            json={"name": name},
            headers=self.headers,
            timeout=15,
        )
        if r.status_code in (200, 201):
            return r.json()["id"]
        # 이미 존재(term_exists) 등의 경우
        data = r.json()
        if isinstance(data, dict) and data.get("data", {}).get("term_id"):
            return data["data"]["term_id"]
        return None

    def _category_ids(self, names: list[str]) -> list[int]:
        ids = []
        for n in names:
            tid = self._get_or_create_term("categories", n)
            if tid:
                ids.append(tid)
        return ids

    def _tag_ids(self, names: list[str]) -> list[int]:
        ids = []
        for n in names:
            tid = self._get_or_create_term("tags", n)
            if tid:
                ids.append(tid)
        return ids

    # ---------- 발행 ----------
    def publish(self, title: str, html: str, *, category: str = "",
                tags: list[str] = None, meta_description: str = "",
                slug: str = "", status: str = "draft",
                publish_date: str = None) -> dict:
        """
        글 발행.
        status: 'publish'(즉시) | 'draft'(초안) | 'future'(예약, publish_date 필요)
        publish_date: ISO8601 예) '2026-08-15T09:00:00'
        반환: {'id', 'link', 'status'}
        """
        payload = {
            "title": title,
            "content": html,
            "status": status,
            "excerpt": meta_description,
        }
        if slug:
            payload["slug"] = slug
        if category:
            cat_ids = self._category_ids([category])
            if cat_ids:
                payload["categories"] = cat_ids
        if tags:
            tag_ids = self._tag_ids(tags)
            if tag_ids:
                payload["tags"] = tag_ids
        if status == "future" and publish_date:
            payload["date"] = publish_date

        r = self.session.post(
            f"{self.base}/posts", json=payload, headers=self.headers, timeout=30
        )
        r.raise_for_status()
        data = r.json()
        return {
            "id": data.get("id"),
            "link": data.get("link"),
            "status": data.get("status"),
        }

    def test_connection(self) -> bool:
        """자격증명 검증."""
        r = self.session.get(
            f"{self.base}/users/me", headers=self.headers, timeout=15
        )
        return r.status_code == 200


def publish_article(article, status: str = None) -> dict:
    """
    content_generator.Article 객체(또는 dict)를 받아 발행.
    DRY_RUN 이면 실제 발행 대신 로컬 저장.
    """
    import json
    from datetime import datetime

    a = article if isinstance(article, dict) else article.to_dict()
    status = status or config.publish_status

    if config.dry_run:
        # 실제 발행 안 하고 파일로 저장
        config.ensure_dirs()
        fname = config.output_dir / f"draft_{a.get('slug','post')}.html"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(f"<!-- title: {a['title']} -->\n")
            f.write(f"<!-- meta: {a.get('meta_description','')} -->\n")
            f.write(f"<!-- tags: {', '.join(a.get('tags', []))} -->\n")
            f.write(a["html"])
        return {"dry_run": True, "saved": str(fname), "status": "local"}

    missing = config.validate(need=("wordpress",))
    if missing:
        raise RuntimeError(f"워드프레스 설정 누락: {', '.join(missing)}")

    pub = WordPressPublisher()
    return pub.publish(
        title=a["title"],
        html=a["html"],
        category=a.get("category", ""),
        tags=a.get("tags", []),
        meta_description=a.get("meta_description", ""),
        slug=a.get("slug", ""),
        status=status,
    )


if __name__ == "__main__":
    missing = config.validate(need=("wordpress",))
    if missing:
        print(f"[!] 워드프레스 설정 누락: {', '.join(missing)}")
    else:
        pub = WordPressPublisher()
        print("연결 테스트:", "성공" if pub.test_connection() else "실패")
