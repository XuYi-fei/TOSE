let dashboardData = null;
let activeResultId = null;
let activeTraceName = null;

const $ = (id) => document.getElementById(id);

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function loadData(keepSelection = true) {
  dashboardData = await fetchJson("/api/data");
  $("generatedAt").textContent = dashboardData.generated_at || "-";
  renderFilters();
  renderResultList(keepSelection);
}

async function rescanData() {
  $("rescanBtn").disabled = true;
  $("rescanBtn").textContent = "扫描中...";
  try {
    await fetchJson("/api/scan");
    await loadData(false);
  } finally {
    $("rescanBtn").disabled = false;
    $("rescanBtn").textContent = "重新扫描结果";
  }
}

function renderFilters() {
  const results = dashboardData.results || [];
  const systems = ["all", ...new Set(results.map((item) => item.system))];
  const algorithms = ["all", ...new Set(results.map((item) => item.algorithm))];
  populateSelect($("systemFilter"), systems);
  populateSelect($("algorithmFilter"), algorithms);
}

function populateSelect(select, items) {
  const current = select.value || "all";
  select.innerHTML = "";
  for (const item of items) {
    const option = document.createElement("option");
    option.value = item;
    option.textContent = item;
    select.appendChild(option);
  }
  select.value = items.includes(current) ? current : items[0];
}

function getFilteredResults() {
  const system = $("systemFilter").value;
  const algorithm = $("algorithmFilter").value;
  return (dashboardData.results || []).filter((result) => {
    if (system !== "all" && result.system !== system) return false;
    if (algorithm !== "all" && result.algorithm !== algorithm) return false;
    return true;
  });
}

function renderResultList(keepSelection) {
  const results = getFilteredResults();
  $("resultCount").textContent = String(results.length);
  const container = $("resultsList");
  container.innerHTML = "";
  if (!results.length) {
    container.innerHTML = `<div class="empty-state">当前筛选条件下没有结果。</div>`;
    clearMainView();
    return;
  }

  if (!keepSelection || !results.some((item) => item.id === activeResultId)) {
    activeResultId = results[0].id;
  }

  for (const result of results) {
    const card = document.createElement("button");
    card.className = `result-card ${result.id === activeResultId ? "active" : ""}`;
    card.innerHTML = `
      <h3>${result.system.toUpperCase()} · ${result.algorithm}</h3>
      <div class="meta">
        <span>clusters ${result.cluster_count}</span>
        <span>FP ${result.fp_count}</span>
        <span>TP ${result.tp_count}</span>
        <span>F1 ${formatNumber(result.f1_score)}</span>
      </div>
    `;
    card.addEventListener("click", () => {
      activeResultId = result.id;
      activeTraceName = null;
      renderResultList(true);
    });
    container.appendChild(card);
  }
  renderActiveResult();
}

function clearMainView() {
  $("overviewGrid").innerHTML = "";
  $("distributionGrid").innerHTML = "";
  $("traceTableBody").innerHTML = "";
  $("traceCount").textContent = "0";
  showDetailEmpty();
}

function renderActiveResult() {
  const result = (dashboardData.results || []).find((item) => item.id === activeResultId);
  if (!result) {
    clearMainView();
    return;
  }
  renderOverview(result);
  renderDistributions(result);
  renderDistributionComparison(result);
  renderTraceTable(result);
}

function renderOverview(result) {
  const selfCheck = result.identity_self_check || {};
  const cards = [
    { label: "辨识分布数", value: result.distribution_count, sub: result.learned_distributions_path || "-" },
    { label: "检测 trace 数", value: result.trace_count, sub: result.test_data_path || "-" },
    { label: "FP / TP", value: `${result.fp_count} / ${result.tp_count}`, sub: `FN ${result.fn_count} · TN ${result.tn_count}` },
    { label: "F1 / Recall", value: `${formatNumber(result.f1_score)} / ${formatNumber(result.recall)}`, sub: `Precision ${formatNumber(result.precision)}` },
    {
      label: "Identity 自检越界占比",
      value: selfCheck.outlier_ratio != null ? `${(selfCheck.outlier_ratio * 100).toFixed(3)}%` : "-",
      sub:
        selfCheck.expected_ratio_3sigma != null
          ? `表示 identity 正常数据中超出自身分布边界的比例；理论 3sigma 约 ${(selfCheck.expected_ratio_3sigma * 100).toFixed(3)}%`
          : "表示 identity 正常数据中超出自身分布边界的比例",
    },
  ];
  $("overviewGrid").innerHTML = cards
    .map(
      (card) => `
        <article class="stat-card">
          <span class="label">${card.label}</span>
          <strong class="value">${card.value}</strong>
          <div class="sub">${card.sub}</div>
        </article>
      `
    )
    .join("");
}

function renderDistributions(result) {
  const container = $("distributionGrid");
  container.innerHTML = "";
  for (const dist of result.distribution_source.distribution_items) {
    const chartId = `dist-${result.id}-${dist.label}`.replace(/[^a-zA-Z0-9_-]/g, "_");
    const card = document.createElement("article");
    card.className = "distribution-card";
    card.innerHTML = `
      <h3>${dist.label}</h3>
      <div class="distribution-meta">
        <div>source: ${escapeHtml(dist.dominant_norm || dist.label)}</div>
        <div>samples: ${dist.sample_count}</div>
        <div>mu: ${formatNumber(dist.mu, 6)}</div>
        <div>sigma: ${formatNumber(dist.sigma, 6)}</div>
        <div>type: ${escapeHtml(dist.distribution_type)}</div>
        <div>context: ${escapeHtml(JSON.stringify(dist.context_features || {}))}</div>
      </div>
      <div id="${chartId}" class="distribution-chart"></div>
    `;
    container.appendChild(card);
    renderDistributionCurve(chartId, dist);
  }
}

function renderDistributionComparison(result) {
  const body = $("comparisonTableBody");
  const rows = result.distribution_comparison || [];
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="6">没有可用的分布对比数据。</td></tr>`;
    return;
  }
  body.innerHTML = rows
    .map((item) => {
      const identity = item.identity_self_check || {};
      const prefix = item.fp_prefix_check || {};
      const identityRatio = Number(identity.outlier_ratio || 0);
      const expectedRatio = Number(identity.expected_ratio_3sigma || 0);
      const prefixRatio = prefix.prefix_outlier_ratio == null ? null : Number(prefix.prefix_outlier_ratio);
      const badge = classifyComparison(identityRatio, expectedRatio, prefixRatio);
      return `
        <tr>
          <td>
            <strong>${escapeHtml(item.label)}</strong><br />
            <span class="hint">主标签 ${escapeHtml(item.dominant_norm || "-")}</span>
          </td>
          <td>${item.sample_count}</td>
          <td>
            mu ${formatNumber(item.mu, 6)}<br />
            sigma ${formatNumber(item.sigma, 6)}<br />
            ${escapeHtml(item.distribution_type)}
          </td>
          <td>
            总点数 ${identity.points ?? "-"}<br />
            越界点 ${identity.outliers ?? "-"}<br />
            越界占比 ${identity.outlier_ratio == null ? "-" : `${(identity.outlier_ratio * 100).toFixed(3)}%`}<br />
            理论 3sigma ${identity.expected_ratio_3sigma == null ? "-" : `${(identity.expected_ratio_3sigma * 100).toFixed(3)}%`}<br />
            <span class="hint">映射来源 ${escapeHtml(formatMatchSource(item.identity_match_source || "-"))}</span>
          </td>
          <td>
            FP trace 数 ${prefix.fp_trace_count ?? 0}<br />
            前缀点数 ${prefix.prefix_points ?? 0}<br />
            前缀越界点 ${prefix.prefix_outliers ?? 0}<br />
            前缀越界占比 ${prefix.prefix_outlier_ratio == null ? "-" : `${(prefix.prefix_outlier_ratio * 100).toFixed(3)}%`}<br />
            <span class="hint">映射来源 ${escapeHtml(formatMatchSource(item.fp_match_source || "-"))}</span>
          </td>
          <td>
            <span class="comparison-badge ${badge.className}">${badge.label}</span>
          </td>
        </tr>
      `;
    })
    .join("");
}

function renderDistributionCurve(chartId, dist) {
  const el = $(chartId);
  if (!el) return;
  const width = 280;
  const height = 120;
  const xs = [];
  const ys = [];
  const sigma = Math.max(Number(dist.sigma) || 1, 1e-6);
  const mu = Number(dist.mu) || 0;
  const minX = mu - sigma * 4;
  const maxX = mu + sigma * 4;
  let maxY = 0;
  for (let i = 0; i < 80; i += 1) {
    const x = minX + ((maxX - minX) * i) / 79;
    const y = gaussianPdf(x, mu, sigma);
    xs.push(x);
    ys.push(y);
    maxY = Math.max(maxY, y);
  }
  const points = xs
    .map((x, idx) => {
      const px = ((x - minX) / (maxX - minX)) * width;
      const py = height - (ys[idx] / (maxY || 1)) * (height - 16) - 8;
      return `${px.toFixed(1)},${py.toFixed(1)}`;
    })
    .join(" ");
  const lower = mu - sigma * 3;
  const upper = mu + sigma * 3;
  const lowerX = ((lower - minX) / (maxX - minX)) * width;
  const upperX = ((upper - minX) / (maxX - minX)) * width;
  el.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${dist.label} distribution">
      <rect x="0" y="0" width="${width}" height="${height}" fill="rgba(255,255,255,0.45)" rx="14"></rect>
      <line x1="${lowerX}" y1="8" x2="${lowerX}" y2="${height - 8}" stroke="rgba(167,44,59,0.45)" stroke-dasharray="4 4"></line>
      <line x1="${upperX}" y1="8" x2="${upperX}" y2="${height - 8}" stroke="rgba(167,44,59,0.45)" stroke-dasharray="4 4"></line>
      <polyline points="${points}" fill="none" stroke="#b74d2f" stroke-width="2.5" stroke-linecap="round"></polyline>
    </svg>
  `;
}

function renderTraceTable(result) {
  const classification = $("classificationFilter").value;
  const query = $("traceSearch").value.trim().toLowerCase();
  const traces = (result.traces || []).filter((trace) => {
    if (classification !== "all" && trace.classification !== classification) return false;
    if (!query) return true;
    return JSON.stringify(trace).toLowerCase().includes(query);
  });
  $("traceCount").textContent = String(traces.length);
  if (!traces.length) {
    $("traceTableBody").innerHTML = `<tr><td colspan="8">没有匹配的 trace。</td></tr>`;
    showDetailEmpty();
    return;
  }
  if (!activeTraceName || !traces.some((trace) => trace.filename === activeTraceName)) {
    activeTraceName = traces[0].filename;
  }
  $("traceTableBody").innerHTML = traces
    .map((trace) => {
      const reason = trace.trigger_reason || {};
      return `
        <tr data-trace="${escapeAttr(trace.filename)}" class="${trace.filename === activeTraceName ? "active-row" : ""}">
          <td>${escapeHtml(shorten(trace.filename, 62))}</td>
          <td class="status-${String(trace.classification).toLowerCase()}">${trace.classification}</td>
          <td>${trace.observed_count_at_trigger ?? trace.total_detection_count ?? "-"}</td>
          <td>${trace.first_detection_time ?? "-"}</td>
          <td>${trace.prefix_point_count ?? "-"}</td>
          <td>${trace.prefix_anomaly_count ?? "-"}</td>
          <td>${trace.trigger_allowed_count ?? "-"}</td>
          <td>${escapeHtml(reason.closest_distribution || "-")} / ${reason.deviation_sigma ? `${formatNumber(reason.deviation_sigma, 2)}σ` : "-"}</td>
        </tr>
      `;
    })
    .join("");
  for (const row of $("traceTableBody").querySelectorAll("tr[data-trace]")) {
    row.addEventListener("click", () => {
      activeTraceName = row.dataset.trace;
      renderTraceTable(result);
      loadTraceDetail(result.id, activeTraceName);
    });
  }
  loadTraceDetail(result.id, activeTraceName);
}

async function loadTraceDetail(resultId, filename) {
  if (!resultId || !filename) return;
  const params = new URLSearchParams({ result_id: resultId, filename });
  const detail = await fetchJson(`/api/trace-detail?${params.toString()}`);
  renderTraceDetail(detail);
}

function renderTraceDetail(detail) {
  $("detailEmpty").classList.add("hidden");
  $("detailContent").classList.remove("hidden");
  $("detailTitle").textContent = shorten(detail.filename, 42);
  const summary = detail.summary;
  const cards = [
    { title: "检测数据长度", value: detail.trace_length },
    { title: "报警位置", value: summary.first_detection_time ?? "-" },
    { title: "报警时前缀点数 n", value: summary.observed_count_at_trigger ?? "-" },
    { title: "报警容忍数", value: summary.trigger_allowed_count ?? "-" },
    { title: "前缀偏离点", value: summary.prefix_anomaly_count ?? "-" },
    { title: "报警累计数", value: summary.trigger_alarm_count ?? "-" },
  ];
  $("detailCards").innerHTML = cards
    .map(
      (card) => `
        <div class="detail-card">
          <span class="title">${card.title}</span>
          <strong class="value">${card.value}</strong>
        </div>
      `
    )
    .join("");
  renderTriggerReason(detail.trigger_reason, summary);
  renderSeriesChart(detail.series, summary);
  renderTriggerWindow(detail.trigger_window);
}

function renderTriggerReason(reason, summary) {
  if (!reason) {
    $("triggerReason").innerHTML = "没有可用的触发点信息。";
    return;
  }
  $("triggerReason").innerHTML = `
    <div class="distribution-meta">
      <div>closest distribution: <strong>${escapeHtml(reason.closest_distribution || "-")}</strong></div>
      <div>distribution type: <strong>${escapeHtml(reason.distribution_type || "-")}</strong></div>
      <div>触发点 value: <strong>${formatNumber(reason.point_value, 6)}</strong></div>
      <div>对应分布 mu / sigma: <strong>${formatNumber(reason.distribution_mu, 6)} / ${formatNumber(reason.distribution_sigma, 6)}</strong></div>
      <div>偏离值: <strong>${formatNumber(reason.deviation_value, 6)}</strong></div>
      <div>偏离程度: <strong>${formatNumber(reason.deviation_sigma, 3)}σ</strong></div>
      <div>best p-value: <strong>${formatNumber(reason.best_p_value, 6)}</strong></div>
      <div>累计 vs 容忍: <strong>${summary.trigger_alarm_count} > ${summary.trigger_allowed_count}</strong></div>
    </div>
    <p class="subtitle" style="margin-top:12px;">${escapeHtml(reason.trigger_explanation || "")}</p>
  `;
}

function renderSeriesChart(series, summary) {
  const host = $("seriesChart");
  const width = 360;
  const height = 240;
  const times = series.map((item) => Number(item.time));
  const values = series.map((item) => Number(item.value));
  const minT = Math.min(...times);
  const maxT = Math.max(...times);
  const minV = Math.min(...values);
  const maxV = Math.max(...values);
  const rangeV = Math.max(maxV - minV, 1e-6);
  const line = series
    .map((item) => {
      const x = ((Number(item.time) - minT) / Math.max(maxT - minT, 1)) * (width - 20) + 10;
      const y = height - ((Number(item.value) - minV) / rangeV) * (height - 30) - 15;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const detectionX =
    summary.first_detection_time == null
      ? null
      : ((Number(summary.first_detection_time) - minT) / Math.max(maxT - minT, 1)) * (width - 20) + 10;
  const abnX =
    summary.abn1_start_time == null
      ? null
      : ((Number(summary.abn1_start_time) - minT) / Math.max(maxT - minT, 1)) * (width - 20) + 10;
  const anomalyDots = series
    .filter((item) => item.is_anomaly)
    .map((item) => {
      const x = ((Number(item.time) - minT) / Math.max(maxT - minT, 1)) * (width - 20) + 10;
      const y = height - ((Number(item.value) - minV) / rangeV) * (height - 30) - 15;
      return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.6" fill="#a72c3b"></circle>`;
    })
    .join("");
  host.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}">
      <rect x="0" y="0" width="${width}" height="${height}" fill="rgba(255,255,255,0.4)" rx="16"></rect>
      ${abnX == null ? "" : `<line x1="${abnX}" y1="12" x2="${abnX}" y2="${height - 12}" stroke="#c77614" stroke-dasharray="5 5"></line>`}
      ${detectionX == null ? "" : `<line x1="${detectionX}" y1="12" x2="${detectionX}" y2="${height - 12}" stroke="#b74d2f" stroke-dasharray="3 4"></line>`}
      <polyline points="${line}" fill="none" stroke="#1f556f" stroke-width="2.2"></polyline>
      ${anomalyDots}
    </svg>
  `;
}

function renderTriggerWindow(rows) {
  $("triggerWindowBody").innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td>${row.time}</td>
          <td>${formatNumber(row.value, 6)}</td>
          <td>${escapeHtml(row.segment_label || "-")}</td>
          <td>${row.is_anomaly ? "yes" : "no"}</td>
          <td>${escapeHtml(row.closest_distribution || "-")}</td>
          <td>${row.best_p_value == null ? "-" : formatNumber(row.best_p_value, 6)}</td>
        </tr>
      `
    )
    .join("");
}

function classifyComparison(identityRatio, expectedRatio, prefixRatio) {
  if (prefixRatio == null) {
    return { label: "无 FP 前缀", className: "prefix-driven" };
  }
  const identityExcess = expectedRatio > 0 ? identityRatio / expectedRatio : 0;
  const prefixExcess = identityRatio > 0 ? prefixRatio / identityRatio : 0;
  if (identityExcess >= 1.3 && prefixExcess < 1.2) {
    return { label: "分布自身偏重尾", className: "data-driven" };
  }
  if (identityExcess < 1.15 && prefixExcess >= 1.5) {
    return { label: "前缀额外偏移", className: "prefix-driven" };
  }
  return { label: "混合因素", className: "mixed" };
}

function formatMatchSource(source) {
  if (!source || source === "-") return "-";
  if (source === "missing") return "缺少统计数据";
  if (source === "unmatched") return "没有匹配到对应分布";
  const [kind, label] = String(source).split(":", 2);
  if (kind === "exact") return `精确匹配 ${label}`;
  if (kind === "dominant") return `按主标签匹配 ${label}`;
  if (kind === "suffix") return `按后缀聚合匹配 ${label}`;
  if (kind === "dominant-suffix") return `按主标签后缀聚合匹配 ${label}`;
  return source;
}

function showDetailEmpty() {
  $("detailEmpty").classList.remove("hidden");
  $("detailContent").classList.add("hidden");
  $("detailTitle").textContent = "选择一条 trace";
}

function gaussianPdf(x, mu, sigma) {
  const coeff = 1 / (sigma * Math.sqrt(2 * Math.PI));
  return coeff * Math.exp(-((x - mu) ** 2) / (2 * sigma ** 2));
}

function formatNumber(value, digits = 4) {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(digits).replace(/\.?0+$/, (match) => (match === ".0000" ? "" : match));
}

function shorten(text, maxLength) {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1)}…`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("'", "&#39;");
}

function bindEvents() {
  $("rescanBtn").addEventListener("click", rescanData);
  $("systemFilter").addEventListener("change", () => renderResultList(false));
  $("algorithmFilter").addEventListener("change", () => renderResultList(false));
  $("classificationFilter").addEventListener("change", () => renderActiveResult());
  $("traceSearch").addEventListener("input", () => renderActiveResult());
}

bindEvents();
loadData(false).catch((error) => {
  console.error(error);
  $("resultsList").innerHTML = `<div class="empty-state">加载失败：${escapeHtml(error.message)}</div>`;
});
