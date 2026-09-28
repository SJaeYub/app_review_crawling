"""크롤링 결과를 CSV/Excel 파일로 변환."""
from __future__ import annotations

import io
from typing import Iterable

import pandas as pd

STORE_LABEL = {"google": "Google Play", "apple": "App Store"}


def _reviews_dataframe(results: Iterable[dict]) -> pd.DataFrame:
    rows = []
    for r in results:
        app_title = (r.get("app_meta") or {}).get("title") or r.get("app_id")
        for rev in r.get("reviews", []):
            rows.append(
                {
                    "스토어": STORE_LABEL.get(r.get("store"), r.get("store")),
                    "앱": app_title,
                    "국가": r.get("country"),
                    "날짜": rev.get("date"),
                    "평점": rev.get("rating"),
                    "작성자": rev.get("author"),
                    "제목": rev.get("title"),
                    "내용": rev.get("content"),
                    "앱버전": rev.get("app_version"),
                }
            )
    columns = ["스토어", "앱", "국가", "날짜", "평점", "작성자", "제목", "내용", "앱버전"]
    return pd.DataFrame(rows, columns=columns)


def _summary_dataframe(results: Iterable[dict]) -> pd.DataFrame:
    rows = []
    for r in results:
        summary = r.get("summary") or {}
        app_title = (r.get("app_meta") or {}).get("title") or r.get("app_id")
        rows.append(
            {
                "스토어": STORE_LABEL.get(r.get("store"), r.get("store")),
                "앱": app_title,
                "국가": r.get("country"),
                "수집 리뷰 수": summary.get("count", 0),
                "평균 평점": summary.get("average_rating"),
                "1점": summary.get("distribution", {}).get("1", 0),
                "2점": summary.get("distribution", {}).get("2", 0),
                "3점": summary.get("distribution", {}).get("3", 0),
                "4점": summary.get("distribution", {}).get("4", 0),
                "5점": summary.get("distribution", {}).get("5", 0),
                "일부만 수집됨": "예" if r.get("truncated") else "아니오",
            }
        )
    return pd.DataFrame(rows)


def build_csv(results: list[dict]) -> bytes:
    df = _reviews_dataframe(results)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8-sig")  # 엑셀 한글 깨짐 방지


def build_xlsx(results: list[dict]) -> bytes:
    reviews_df = _reviews_dataframe(results)
    summary_df = _summary_dataframe(results)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="요약", index=False)
        reviews_df.to_excel(writer, sheet_name="리뷰", index=False)
    return buf.getvalue()
