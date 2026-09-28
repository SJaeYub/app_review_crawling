"""Apple App Store 앱 검색 및 리뷰 수집.

공식 API가 아닌, 애플이 공개적으로 제공하는 두 엔드포인트를 사용한다.
  - 앱 검색: iTunes Search API (https://itunes.apple.com/search)
  - 리뷰 조회: 고객 리뷰 RSS 피드(JSON) - 스토어별 최신순 정렬, 최대 10페이지(약 500건)까지만 제공됨.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import requests

STORE = "apple"

SEARCH_URL = "https://itunes.apple.com/search"
RSS_URL_TMPL = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"

# 애플 리뷰 RSS는 페이지당 약 50건, 최대 10페이지까지만 제공한다.
MAX_PAGES = 10
REQUEST_TIMEOUT = 15


def search_apps(query: str, country: str = "kr", limit: int = 10) -> list[dict]:
    params = {"term": query, "country": country, "entity": "software", "limit": limit}
    resp = requests.get(SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return [
        {
            "store": STORE,
            "app_id": str(item["trackId"]),
            "title": item.get("trackName"),
            "developer": item.get("artistName"),
            "icon": item.get("artworkUrl60"),
            "score": item.get("averageUserRating"),
        }
        for item in data.get("results", [])
    ]


def get_app_info(app_id: str, country: str = "kr") -> dict:
    params = {"id": app_id, "country": country, "entity": "software"}
    resp = requests.get("https://itunes.apple.com/lookup", params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    if not results:
        raise ValueError(f"앱스토어에서 앱을 찾을 수 없습니다: {app_id}")
    item = results[0]
    return {
        "store": STORE,
        "app_id": app_id,
        "title": item.get("trackName"),
        "developer": item.get("artistName"),
        "icon": item.get("artworkUrl60"),
        "score": item.get("averageUserRating"),
    }


def _text(entry: dict, key: str) -> Optional[str]:
    node = entry.get(key)
    if isinstance(node, dict):
        return node.get("label")
    return None


def _author_name(entry: dict) -> Optional[str]:
    author = entry.get("author")
    if isinstance(author, dict):
        name = author.get("name")
        if isinstance(name, dict):
            return name.get("label")
        if isinstance(name, str):
            return name
    return None


def fetch_reviews(
    app_id: str,
    country: str,
    start_date: date,
    end_date: date,
) -> tuple[list[dict], bool]:
    """start_date~end_date(포함) 사이의 리뷰를 최신순으로 수집한다.

    Returns:
        (reviews, truncated) - truncated는 애플 RSS의 페이지 제한(MAX_PAGES)에 걸려
        start_date까지 도달하지 못하고 중단했는지 여부.
    """
    collected: list[dict] = []
    truncated = False

    for page in range(1, MAX_PAGES + 1):
        url = RSS_URL_TMPL.format(country=country, page=page, app_id=app_id)
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 404:
            break
        resp.raise_for_status()
        try:
            data = resp.json()
        except ValueError:
            break

        entries = data.get("feed", {}).get("entry")
        if not entries:
            break
        if isinstance(entries, dict):
            entries = [entries]

        reached_start = False
        has_review = False
        for entry in entries:
            if "im:rating" not in entry:
                # 첫 엔트리는 앱 자체 메타데이터인 경우가 있어 건너뜀
                continue
            has_review = True
            updated = _text(entry, "updated")
            if not updated:
                continue
            review_date = date.fromisoformat(updated[:10])
            if review_date > end_date:
                continue
            if review_date < start_date:
                reached_start = True
                break
            collected.append(
                {
                    "store": STORE,
                    "author": _author_name(entry),
                    "rating": int(entry["im:rating"]["label"]),
                    "title": _text(entry, "title"),
                    "content": _text(entry, "content"),
                    "date": review_date.isoformat(),
                    "app_version": _text(entry, "im:version"),
                }
            )

        if reached_start:
            break
        if not has_review:
            break
    else:
        # MAX_PAGES까지 다 조회했지만 아직 start_date 이전 리뷰를 못 만난 경우
        truncated = True

    return collected, truncated
