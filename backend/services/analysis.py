"""리뷰 목록에서 요약 통계(평균 평점, 평점 분포, 일자별 추이)를 계산."""
from __future__ import annotations

from collections import defaultdict


def compute_summary(reviews: list[dict]) -> dict:
    count = len(reviews)
    distribution = {str(i): 0 for i in range(1, 6)}
    daily: dict[str, list[int]] = defaultdict(list)

    total = 0
    rated = 0
    for r in reviews:
        rating = r.get("rating")
        if rating is None:
            continue
        rating = int(rating)
        if 1 <= rating <= 5:
            distribution[str(rating)] += 1
        total += rating
        rated += 1
        daily[r.get("date")].append(rating)

    average_rating = round(total / rated, 2) if rated else None

    daily_list = [
        {
            "date": d,
            "count": len(ratings),
            "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        }
        for d, ratings in sorted(daily.items())
    ]

    return {
        "count": count,
        "average_rating": average_rating,
        "distribution": distribution,
        "daily": daily_list,
    }
