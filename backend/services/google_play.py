"""Google Play(구글 플레이 스토어) 앱 검색 및 리뷰 수집."""
from __future__ import annotations

from datetime import date
from typing import Optional

from google_play_scraper import Sort
from google_play_scraper import reviews as gp_reviews
from google_play_scraper import search as gp_search
from google_play_scraper.exceptions import NotFoundError

STORE = "google"

# 한 번에 서버로 요청할 리뷰 배치 크기
BATCH_SIZE = 200
# 무한정 오래 걸리는 것을 막기 위한 최대 요청 횟수 (BATCH_SIZE * MAX_REQUESTS 건까지 조회)
MAX_REQUESTS = 50


def search_apps(query: str, country: str = "kr", lang: str = "ko", n_hits: int = 10) -> list[dict]:
    results = gp_search(query, lang=lang, country=country, n_hits=n_hits)
    return [
        {
            "store": STORE,
            "app_id": r["appId"],
            "title": r.get("title"),
            "developer": r.get("developer"),
            "icon": r.get("icon"),
            "score": r.get("score"),
        }
        for r in results
    ]


def get_app_info(app_id: str, country: str = "kr", lang: str = "ko") -> dict:
    from google_play_scraper import app as gp_app

    info = gp_app(app_id, lang=lang, country=country)
    return {
        "store": STORE,
        "app_id": app_id,
        "title": info.get("title"),
        "developer": info.get("developer"),
        "icon": info.get("icon"),
        "score": info.get("score"),
    }


def fetch_reviews(
    app_id: str,
    country: str,
    start_date: date,
    end_date: date,
    lang: str = "ko",
    max_reviews: int = 10000,
) -> tuple[list[dict], bool]:
    """start_date~end_date(포함) 사이의 리뷰를 최신순으로 수집한다.

    Returns:
        (reviews, truncated) - truncated는 max_reviews/최대 요청 횟수에 도달해
        더 오래된 리뷰를 확인하지 못하고 중단했는지 여부.
    """
    collected: list[dict] = []
    token: Optional[str] = None
    truncated = False

    try:
        for _ in range(MAX_REQUESTS):
            batch, token = gp_reviews(
                app_id,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=BATCH_SIZE,
                continuation_token=token,
            )
            if not batch:
                break

            reached_start = False
            for r in batch:
                at = r.get("at")
                if at is None:
                    continue
                review_date = at.date()
                if review_date > end_date:
                    continue
                if review_date < start_date:
                    reached_start = True
                    break
                collected.append(
                    {
                        "store": STORE,
                        "author": r.get("userName"),
                        "rating": r.get("score"),
                        "title": None,
                        "content": r.get("content"),
                        "date": review_date.isoformat(),
                        "app_version": r.get("reviewCreatedVersion"),
                    }
                )

            if reached_start:
                break
            if len(collected) >= max_reviews:
                truncated = True
                break
            if token is None:
                break
        else:
            # MAX_REQUESTS에 도달했지만 아직 start_date 이전 리뷰를 못 만난 경우
            truncated = True
    except NotFoundError as exc:
        raise ValueError(f"구글 플레이에서 앱을 찾을 수 없습니다: {app_id}") from exc

    return collected, truncated
