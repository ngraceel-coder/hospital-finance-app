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

    # ---------- 미디어 업로드 ----------
    def upload_media(self, filepath, filename: str = None) -> Optional[dict]:
        """이미지 업로드 후 {'id', 'url'} 반환. 실패 시 None."""
        import os as _os
        import mimetypes

        filepath = str(filepath)
        filename = filename or _os.path.basename(filepath)
        mime = mimetypes.guess_type(filename)[0] or "image/png"
        with open(filepath, "rb") as f:
            data = f.read()
        headers = dict(self.headers)
        headers["Content-Type"] = mime
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        r = self.session.post(
            f"{self.base}/media", data=data, headers=headers, timeout=60
        )
        if r.status_code in (200, 201):
            j = r.json()
            return {"id": j.get("id"), "url": j.get("source_url", "")}
        print(f"   [i] 미디어 업로드 실패({r.status_code})")
        return None

    # ---------- 발행 ----------
    def publish(self, title: str, html: str, *, category: str = "",
                tags: list[str] = None, meta_description: str = "",
                slug: str = "", status: str = "draft",
                publish_date: str = None, featured_media: int = None) -> dict:
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
        if featured_media:
            payload["featured_media"] = featured_media

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


def publish_article(article, status: str = None, thumbnail=None, photo=None) -> dict:
    """
    content_generator.Article 객체(또는 dict)를 받아 발행.
    thumbnail: 대표이미지 파일 경로(선택) — 업로드 후 featured image로 설정.
    photo: 본문 사진 파일 경로(선택) — 업로드 후 PHOTO_PLACEHOLDER 를 실제 URL로 치환.
    DRY_RUN 이면 실제 발행 대신 로컬 저장.
    """
    import json
    import re as _re
    from datetime import datetime

    a = article if isinstance(article, dict) else article.to_dict()
    status = status or config.publish_status

    def _strip_placeholder(html: str) -> str:
        """사진 업로드가 안 됐을 때 깨진 이미지 태그가 남지 않도록 제거."""
        return _re.sub(r"<figure><img src=\"PHOTO_PLACEHOLDER\"[^>]*/></figure>", "", html)

    if config.dry_run:
        # 실제 발행 안 하고 파일로 저장
        a["html"] = _strip_placeholder(a["html"])
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
    media_id = None
    if thumbnail:
        m = pub.upload_media(thumbnail)
        media_id = m["id"] if m else None
    # 본문 사진: 업로드 성공 시 URL 치환, 실패 시 깨진 태그 제거
    if photo and "PHOTO_PLACEHOLDER" in a["html"]:
        pm = pub.upload_media(photo)
        if pm and pm.get("url"):
            a["html"] = a["html"].replace("PHOTO_PLACEHOLDER", pm["url"])
        else:
            a["html"] = _strip_placeholder(a["html"])
    else:
        a["html"] = _strip_placeholder(a["html"])
    return pub.publish(
        title=a["title"],
        html=a["html"],
        category=a.get("category", ""),
        tags=a.get("tags", []),
        meta_description=a.get("meta_description", ""),
        slug=a.get("slug", ""),
        status=status,
        featured_media=media_id,
    )


if __name__ == "__main__":
    missing = config.validate(need=("wordpress",))
    if missing:
        print(f"[!] 워드프레스 설정 누락: {', '.join(missing)}")
    else:
        pub = WordPressPublisher()
        print("연결 테스트:", "성공" if pub.test_connection() else "실패")
