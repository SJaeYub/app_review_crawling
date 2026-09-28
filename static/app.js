(() => {
  "use strict";

  const STORE_LABEL = { google: "Google Play", apple: "App Store" };
  const PAGE_SIZE = 50;

  const state = {
    selected: [], // {store, app_id, country, title, developer, icon}
    lastResponse: null, // 마지막 /api/reviews 응답 (다운로드용)
    tablePages: {}, // key(store:app_id) -> 현재 표시된 리뷰 수
  };

  const $ = (sel) => document.querySelector(sel);

  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setStatus(message, isError = false) {
    const el = $("#status-area");
    el.textContent = message || "";
    el.classList.toggle("error", !!isError);
  }

  function targetKey(t) {
    return `${t.store}:${t.app_id}`;
  }

  // ---------- 검색 ----------

  async function searchStore(store, query, country) {
    const url = `/api/search?store=${encodeURIComponent(store)}&query=${encodeURIComponent(query)}&country=${encodeURIComponent(country)}`;
    const resp = await fetch(url);
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `${STORE_LABEL[store]} 검색 실패`);
    }
    return resp.json();
  }

  function renderSearchResults(sections) {
    const container = $("#search-results");
    container.innerHTML = "";
    sections.forEach(({ store, items, error }) => {
      const col = document.createElement("div");
      col.className = "search-column";
      const heading = document.createElement("h3");
      heading.textContent = STORE_LABEL[store];
      col.appendChild(heading);

      if (error) {
        const p = document.createElement("p");
        p.style.color = "#dc2626";
        p.style.fontSize = "12px";
        p.textContent = error;
        col.appendChild(p);
      } else if (!items.length) {
        const p = document.createElement("p");
        p.style.color = "#6b7280";
        p.style.fontSize = "12px";
        p.textContent = "검색 결과가 없습니다.";
        col.appendChild(p);
      } else {
        items.forEach((item) => {
          const row = document.createElement("div");
          row.className = "app-item";
          row.innerHTML = `
            <img src="${escapeHtml(item.icon || "")}" alt="" onerror="this.style.visibility='hidden'" />
            <div class="info">
              <div class="title">${escapeHtml(item.title)}</div>
              <div class="meta">${escapeHtml(item.developer || "")} ${item.score ? "· ★" + Number(item.score).toFixed(1) : ""}</div>
            </div>
            <button type="button" data-action="add">추가</button>
          `;
          row.querySelector('[data-action="add"]').addEventListener("click", () => addTarget(item));
          col.appendChild(row);
        });
      }
      container.appendChild(col);
    });
  }

  async function handleSearch() {
    const query = $("#app-name").value.trim();
    const country = ($("#country").value || "kr").trim().toLowerCase();
    const useGoogle = $("#store-google").checked;
    const useApple = $("#store-apple").checked;

    if (!query) {
      setStatus("앱 이름을 입력해주세요.", true);
      return;
    }
    if (!useGoogle && !useApple) {
      setStatus("최소 하나의 스토어를 선택해주세요.", true);
      return;
    }

    setStatus("검색 중...");
    const stores = [];
    if (useGoogle) stores.push("google");
    if (useApple) stores.push("apple");

    const sections = await Promise.all(
      stores.map(async (store) => {
        try {
          const items = await searchStore(store, query, country);
          return { store, items };
        } catch (e) {
          return { store, items: [], error: e.message };
        }
      })
    );
    renderSearchResults(sections);
    setStatus("");
  }

  // ---------- 선택된 앱 ----------

  function addTarget(item) {
    const exists = state.selected.some((t) => t.store === item.store && t.app_id === item.app_id);
    if (exists) return;
    state.selected.push({
      store: item.store,
      app_id: item.app_id,
      country: ($("#country").value || "kr").trim().toLowerCase(),
      title: item.title,
      developer: item.developer,
      icon: item.icon,
    });
    renderChips();
  }

  function removeTarget(key) {
    state.selected = state.selected.filter((t) => targetKey(t) !== key);
    renderChips();
  }

  function renderChips() {
    const list = $("#chip-list");
    list.innerHTML = "";
    state.selected.forEach((t) => {
      const chip = document.createElement("div");
      chip.className = "chip";
      chip.innerHTML = `
        <span class="badge ${t.store}">${STORE_LABEL[t.store]}</span>
        <span>${escapeHtml(t.title)}</span>
        <span class="remove" data-key="${targetKey(t)}">&times;</span>
      `;
      chip.querySelector(".remove").addEventListener("click", (e) => removeTarget(e.target.dataset.key));
      list.appendChild(chip);
    });
    $("#btn-crawl").disabled = state.selected.length === 0;
  }

  // ---------- 크롤링 ----------

  async function handleCrawl() {
    const startDate = $("#start-date").value;
    const endDate = $("#end-date").value;
    if (!startDate || !endDate) {
      setStatus("시작일과 종료일을 모두 선택해주세요.", true);
      return;
    }
    if (startDate > endDate) {
      setStatus("종료일은 시작일보다 빠를 수 없습니다.", true);
      return;
    }
    if (state.selected.length === 0) {
      setStatus("리뷰를 가져올 앱을 먼저 선택해주세요.", true);
      return;
    }

    const btn = $("#btn-crawl");
    btn.disabled = true;
    setStatus("리뷰를 수집하는 중입니다... 기간이 길거나 리뷰가 많으면 다소 시간이 걸릴 수 있습니다.");

    const body = {
      targets: state.selected.map((t) => ({ store: t.store, app_id: t.app_id, country: t.country, title: t.title })),
      start_date: startDate,
      end_date: endDate,
      lang: "ko",
    };

    try {
      const resp = await fetch("/api/reviews", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || "리뷰 수집에 실패했습니다.");
      }
      const data = await resp.json();
      state.lastResponse = data;
      state.tablePages = {};
      renderResults(data);
      setStatus("완료되었습니다.");
    } catch (e) {
      setStatus(e.message, true);
    } finally {
      btn.disabled = false;
    }
  }

  // ---------- 결과 렌더링 ----------

  function renderRatingBars(distribution) {
    const max = Math.max(1, ...Object.values(distribution));
    const rows = [5, 4, 3, 2, 1]
      .map((star) => {
        const count = distribution[String(star)] || 0;
        const pct = Math.round((count / max) * 100);
        return `
          <div class="bar-row">
            <div class="bar-label">${star}점</div>
            <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
            <div class="bar-count">${count}</div>
          </div>
        `;
      })
      .join("");
    return `<div class="bar-chart">${rows}</div>`;
  }

  function renderDailyChart(daily) {
    if (!daily.length) return "<p style='font-size:12px;color:#6b7280;'>데이터가 없습니다.</p>";
    const max = Math.max(1, ...daily.map((d) => d.count));
    const bars = daily
      .map((d) => {
        const height = Math.max(2, Math.round((d.count / max) * 100));
        const title = `${d.date} · ${d.count}건 · 평균 ${d.average_rating ?? "-"}점`;
        return `<div class="day-bar" style="height:${height}%" title="${escapeHtml(title)}"></div>`;
      })
      .join("");
    return `<div class="daily-chart">${bars}</div>`;
  }

  function renderReviewTableRows(reviews) {
    return reviews
      .map(
        (r) => `
        <tr>
          <td>${escapeHtml(r.date)}</td>
          <td>${r.rating ?? "-"}</td>
          <td>${escapeHtml(r.author)}</td>
          <td class="content">${escapeHtml(r.title ? r.title + "\n" : "")}${escapeHtml(r.content)}</td>
        </tr>
      `
      )
      .join("");
  }

  function renderResultCard(result) {
    const key = `${result.store}:${result.app_id}`;
    const title = result.app_meta && result.app_meta.title ? result.app_meta.title : result.app_id;
    const wrap = document.createElement("div");
    wrap.className = "card result-card";

    if (result.error) {
      wrap.innerHTML = `
        <div class="result-header">
          <h3><span class="badge ${result.store}">${STORE_LABEL[result.store]}</span> ${escapeHtml(title)}</h3>
        </div>
        <p class="warning">이 앱의 리뷰를 가져오지 못했습니다: ${escapeHtml(result.error)}</p>
      `;
      return wrap;
    }

    state.tablePages[key] = PAGE_SIZE;
    const summary = result.summary;

    wrap.innerHTML = `
      <div class="result-header">
        <h3><span class="badge ${result.store}">${STORE_LABEL[result.store]}</span> ${escapeHtml(title)} <small style="color:#6b7280;font-weight:400;">(${result.country})</small></h3>
      </div>
      ${result.truncated ? `<p class="warning">리뷰 수가 많아 일부(최근 리뷰 중 조회 가능한 범위)만 수집되었습니다.</p>` : ""}
      <div class="summary-stats">
        <div class="stat"><div class="value">${summary.count}</div><div class="label">수집 리뷰 수</div></div>
        <div class="stat"><div class="value">${summary.average_rating ?? "-"}</div><div class="label">평균 평점</div></div>
      </div>
      <h4 style="font-size:13px;margin-bottom:6px;">평점 분포</h4>
      ${renderRatingBars(summary.distribution)}
      <h4 style="font-size:13px;margin-bottom:6px;">일자별 리뷰 수</h4>
      ${renderDailyChart(summary.daily)}
      <h4 style="font-size:13px;margin:16px 0 6px;">리뷰 목록</h4>
      <div class="table-wrap">
        <table class="review-table">
          <thead><tr><th>날짜</th><th>평점</th><th>작성자</th><th>내용</th></tr></thead>
          <tbody class="review-tbody"></tbody>
        </table>
      </div>
      <div class="load-more"><button type="button" class="secondary btn-load-more">더 보기</button></div>
    `;

    const tbody = wrap.querySelector(".review-tbody");
    const loadMoreWrap = wrap.querySelector(".load-more");
    const loadMoreBtn = wrap.querySelector(".btn-load-more");

    function renderPage() {
      const limit = state.tablePages[key];
      tbody.innerHTML = renderReviewTableRows(result.reviews.slice(0, limit));
      loadMoreWrap.classList.toggle("hidden", limit >= result.reviews.length);
    }

    loadMoreBtn.addEventListener("click", () => {
      state.tablePages[key] += PAGE_SIZE;
      renderPage();
    });

    renderPage();
    return wrap;
  }

  function renderResults(data) {
    const section = $("#results-section");
    const container = $("#results-container");
    container.innerHTML = "";
    data.results.forEach((r) => container.appendChild(renderResultCard(r)));
    section.classList.remove("hidden");
  }

  // ---------- 다운로드 ----------

  async function handleExport(format) {
    if (!state.lastResponse) return;
    setStatus("파일을 생성하는 중입니다...");
    try {
      const resp = await fetch("/api/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          format,
          results: state.lastResponse.results,
          filename: `app_reviews_${state.lastResponse.start_date}_${state.lastResponse.end_date}`,
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || "다운로드에 실패했습니다.");
      }
      const blob = await resp.blob();
      const disposition = resp.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match ? match[1] : `app_reviews.${format}`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setStatus("다운로드가 완료되었습니다.");
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  // ---------- 초기화 ----------

  function setDefaultDates() {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    const fmt = (d) => d.toISOString().slice(0, 10);
    $("#start-date").value = fmt(start);
    $("#end-date").value = fmt(end);
  }

  document.addEventListener("DOMContentLoaded", () => {
    setDefaultDates();
    $("#btn-search").addEventListener("click", handleSearch);
    $("#app-name").addEventListener("keydown", (e) => {
      if (e.key === "Enter") handleSearch();
    });
    $("#btn-crawl").addEventListener("click", handleCrawl);
    $("#btn-export-csv").addEventListener("click", () => handleExport("csv"));
    $("#btn-export-xlsx").addEventListener("click", () => handleExport("xlsx"));
  });
})();
