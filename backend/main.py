from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.schemas import ExportRequest, ReviewsRequest, ReviewsResponse, SearchResult, Store, StoreResult
from backend.services import app_store, google_play
from backend.services.analysis import compute_summary
from backend.services.export import build_csv, build_xlsx

logger = logging.getLogger("app_review_crawling")
logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="앱 리뷰 크롤러")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/search", response_model=list[SearchResult])
def search(
    store: Store = Query(...),
    query: str = Query(..., min_length=1),
    country: str = Query("kr"),
    lang: str = Query("ko"),
):
    country = country.strip().lower()
    try:
        if store == "google":
            results = google_play.search_apps(query, country=country, lang=lang)
        else:
            results = app_store.search_apps(query, country=country)
    except Exception as exc:  # noqa: BLE001
        logger.exception("search failed")
        raise HTTPException(status_code=502, detail=f"검색 중 오류가 발생했습니다: {exc}") from exc

    if not results:
        raise HTTPException(status_code=404, detail="검색 결과가 없습니다. 앱 이름이나 국가 코드를 확인해주세요.")
    return results


@app.post("/api/reviews", response_model=ReviewsResponse)
def get_reviews(req: ReviewsRequest):
    results: list[StoreResult] = []

    for target in req.targets:
        try:
            if target.store == "google":
                app_meta = google_play.get_app_info(target.app_id, country=target.country, lang=req.lang)
                reviews, truncated = google_play.fetch_reviews(
                    target.app_id,
                    country=target.country,
                    start_date=req.start_date,
                    end_date=req.end_date,
                    lang=req.lang,
                )
            else:
                app_meta = app_store.get_app_info(target.app_id, country=target.country)
                reviews, truncated = app_store.fetch_reviews(
                    target.app_id,
                    country=target.country,
                    start_date=req.start_date,
                    end_date=req.end_date,
                )
            summary = compute_summary(reviews)
            results.append(
                StoreResult(
                    store=target.store,
                    app_id=target.app_id,
                    country=target.country,
                    app_meta=app_meta,
                    summary=summary,
                    reviews=reviews,
                    truncated=truncated,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("crawl failed for %s/%s", target.store, target.app_id)
            results.append(
                StoreResult(
                    store=target.store,
                    app_id=target.app_id,
                    country=target.country,
                    app_meta={"title": target.title},
                    summary=compute_summary([]),
                    reviews=[],
                    truncated=False,
                    error=str(exc),
                )
            )

    return ReviewsResponse(start_date=req.start_date, end_date=req.end_date, results=results)


@app.post("/api/export")
def export(req: ExportRequest):
    results = [r.model_dump() for r in req.results]
    filename = req.filename or "app_reviews"

    if req.format == "csv":
        content = build_csv(results)
        media_type = "text/csv"
        filename = f"{filename}.csv"
    else:
        content = build_xlsx(results)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{filename}.xlsx"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
