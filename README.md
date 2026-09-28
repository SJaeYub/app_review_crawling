# 앱 리뷰 크롤러

앱 이름과 기간을 입력하면 **Google Play(구글 플레이 스토어)** 와 **Apple App Store(애플 앱스토어)** 의 리뷰·평점을 조회해 웹 화면에서 확인하고 CSV/Excel로 내려받을 수 있는 사이트입니다.

## 주요 기능

- 앱 이름으로 검색 → 후보 목록(아이콘/개발사 포함)에서 정확한 앱을 선택
- 국가 코드 지정 (기본값 `kr`, 스토어별로 리뷰가 다르게 노출됨)
- 시작일 ~ 종료일 기간 지정 후 해당 기간 리뷰만 수집
- 결과 화면: 총 리뷰 수, 평균 평점, 평점(1~5점) 분포, 일자별 리뷰 수 차트, 리뷰 목록 테이블
- CSV / Excel(.xlsx) 다운로드 (Excel은 요약 시트 + 리뷰 시트 포함)
- 구글 플레이·앱스토어를 동시에 선택해 한 화면에서 비교 가능

## 데이터 출처 및 한계

- **Google Play**: [`google-play-scraper`](https://pypi.org/project/google-play-scraper/) 라이브러리로 구글 플레이 웹페이지의 공개 리뷰 데이터를 조회합니다. 최신순으로 페이지네이션하며 지정한 시작일 이전 리뷰가 나오면 자동으로 중단합니다. 다만 매우 오래된 기간을 아주 인기 많은 앱에 대해 조회하면 시간이 오래 걸리거나 내부 상한(최대 요청 50회, 약 1만 건)에 걸려 일부만 조회될 수 있습니다.
- **App Store**: 애플이 공개 제공하는 iTunes Search API(앱 검색)와 고객 리뷰 RSS 피드(리뷰 조회)를 사용합니다. **App Store 고객 리뷰 RSS는 정책상 최신순 최대 10페이지(약 500건) 까지만 제공**되므로, 그보다 오래된 리뷰나 그 이상 건수는 조회할 수 없습니다. (공식 API로 전체 리뷰 이력을 받는 방법은 없습니다.)
- 두 스토어 모두 비공식/공개 데이터 조회이므로, 스토어 정책 변경 시 동작이 달라질 수 있습니다.

## 로컬 실행 방법

### 1. 의존성 설치

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 서버 실행

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 접속

브라우저에서 `http://localhost:8000` 접속

## 프로젝트 구조

```
app_review_crawling/
├── backend/
│   ├── main.py              # FastAPI 앱 (API 라우트, 정적 파일 서빙)
│   ├── schemas.py           # 요청/응답 Pydantic 모델
│   └── services/
│       ├── google_play.py   # 구글 플레이 검색/리뷰 수집
│       ├── app_store.py     # 앱스토어 검색/리뷰 수집
│       ├── analysis.py      # 평점 요약 통계 계산
│       └── export.py        # CSV/Excel 파일 생성
├── static/
│   ├── index.html
│   ├── app.js
│   └── style.css
└── requirements.txt
```

## API 요약

- `GET /api/search?store=google|apple&query=앱이름&country=kr` — 앱 후보 검색
- `POST /api/reviews` — `{targets:[{store,app_id,country}], start_date, end_date, lang}` 로 기간별 리뷰 수집
- `POST /api/export` — `{format: "csv"|"xlsx", results: [...]}` 로 파일 다운로드
