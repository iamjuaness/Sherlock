// Sherlock - Main Dashboard script
let globalStatsData = null;
let adminSummary = null; // /api/v1/admin/dashboard/summary (KPIs, Brier, CLV, calibración)
let adminAnomalies = null; // /api/v1/admin/stats/anomalies
let activeCategory = "global"; // 'global', 'professional', 'underdog'
let firstRenderDone = false;

// Chart instances
let marketChartInstance = null;
let oddsChartInstance = null;
let edgeChartInstance = null;
let confChartInstance = null;
let calibChartInstance = null;
let dailyProfitChartInstance = null;

const PALETTE = {
  accent: "#22d3ee",
  pos: "#34d399",
  neg: "#fb7185",
  warn: "#fbbf24",
  info: "#818cf8",
  text: "#e6edf6",
  text2: "#9aa7b8",
  grid: "rgba(148, 163, 184, 0.1)",
};
const REDUCED_MOTION =
  window.matchMedia &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function esc(v) {
  return String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
}
const $ = (id) => document.getElementById(id);
const setText = (id, txt) => {
  const el = $(id);
  if (el) el.textContent = txt;
  return el;
};
const signed = (v, d = 2, suffix = "") =>
  `${v > 0 ? "+" : ""}${Number(v).toFixed(d)}${suffix}`;
const tone = (v) => (v > 0 ? "sx-pos" : v < 0 ? "sx-neg" : "");

function setTone(el, v) {
  if (!el) return;
  el.classList.remove("sx-pos", "sx-neg", "sx-warn");
  const t = tone(v);
  if (t) el.classList.add(t);
}

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  // Signal active=false since we navigated away from leagues view
  fetch("/api/v1/leagues/active-state?active=false", { method: "POST" }).catch(
    () => {},
  );

  // Sync checkbox with localStorage
  const useStakeCheck = $("dashboard-use-stake");
  if (useStakeCheck) {
    const saved = localStorage.getItem("use_stake_system");
    if (saved !== null) {
      useStakeCheck.checked = saved === "true";
    } else {
      localStorage.setItem("use_stake_system", "true");
    }
  }

  const useGeneralCheck = $("dashboard-use-general-stats");
  const generalStatsDate = $("dashboard-general-stats-date");
  if (useGeneralCheck) {
    const savedGen = localStorage.getItem("use_general_stats_system");
    if (savedGen !== null) {
      useGeneralCheck.checked = savedGen === "true";
    } else {
      localStorage.setItem("use_general_stats_system", "false");
      useGeneralCheck.checked = false;
    }

    if (generalStatsDate) {
      const savedDate = localStorage.getItem("general_stats_threshold_date");
      if (savedDate) {
        generalStatsDate.value = savedDate;
      } else {
        generalStatsDate.value = "2026-01-01";
        localStorage.setItem("general_stats_threshold_date", "2026-01-01");
      }
      generalStatsDate.style.display = useGeneralCheck.checked
        ? "inline-block"
        : "none";
    }
  }

  fetchGlobalStats();
  startResultPolling();

  // Setup Simulator button
  const simBtn = $("btn-simulate");
  if (simBtn) simBtn.addEventListener("click", updateCapitalSimulator);
});

// Helper to get selected date range parameters for dashboard.
// Returns { all: "?date_from=..&use_stake=..", range: "?date_from=..&date_to=.." }
function buildDashboardParams() {
  const rangeEl = $("dashboard-date-range");
  const range = rangeEl ? rangeEl.value : "all";
  let dateFrom = "";
  let dateTo = "";

  function formatLocalDateTime(date, time = "00:00:00") {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}T${time}`;
  }
  const daysAgo = (n) => {
    const d = new Date();
    d.setDate(d.getDate() - n);
    return formatLocalDateTime(d, "00:00:00");
  };

  if (range === "today") {
    const today = new Date();
    dateFrom = formatLocalDateTime(today, "00:00:00");
    dateTo = formatLocalDateTime(today, "23:59:59");
  } else if (range === "7days") {
    dateFrom = daysAgo(7);
  } else if (range === "3days") {
    dateFrom = daysAgo(3);
  } else if (range === "30days") {
    dateFrom = daysAgo(30);
  } else if (range === "custom") {
    const fromVal = $("dashboard-date-from")?.value || "";
    const toVal = $("dashboard-date-to")?.value || "";
    if (fromVal) dateFrom = `${fromVal}T00:00:00`;
    if (toVal) dateTo = `${toVal}T23:59:59`;
  }

  const rangeParams = [];
  if (dateFrom) rangeParams.push(`date_from=${encodeURIComponent(dateFrom)}`);
  if (dateTo) rangeParams.push(`date_to=${encodeURIComponent(dateTo)}`);

  const allParams = [...rangeParams];
  if ($("dashboard-use-stake")?.checked) allParams.push("use_stake=true");
  if ($("dashboard-use-general-stats")?.checked)
    allParams.push("use_general_stats=true");

  const q = (arr) => (arr.length ? "?" + arr.join("&") : "");
  return { all: q(allParams), range: q(rangeParams) };
}

function getDashboardDateParams() {
  return buildDashboardParams().all;
}

function handleDashboardDateRangeChange() {
  const range = $("dashboard-date-range").value;
  const customInputs = $("dashboard-custom-date-inputs");
  if (customInputs) {
    customInputs.style.display = range === "custom" ? "inline-flex" : "none";
  }
  reloadDashboardStats();
}

async function reloadDashboardStats() {
  const useStakeCheck = $("dashboard-use-stake");
  if (useStakeCheck) {
    localStorage.setItem("use_stake_system", useStakeCheck.checked);
  }
  const useGeneralCheck = $("dashboard-use-general-stats");
  if (useGeneralCheck) {
    localStorage.setItem("use_general_stats_system", useGeneralCheck.checked);
  }
  await fetchGlobalStats();
}

function showLoader(message) {
  const loader = $("loader");
  const content = $("dashboard-content");
  if (loader) {
    loader.style.display = "flex";
    loader.innerHTML = `<div class="spinner"></div><span>${esc(message)}</span>`;
  }
  if (content) content.style.display = "none";
}

async function triggerRecalculateAndFetch() {
  const useGeneralCheck = $("dashboard-use-general-stats");
  const generalStatsDate = $("dashboard-general-stats-date");
  const useGeneral = useGeneralCheck ? useGeneralCheck.checked : false;
  const thresholdDate = generalStatsDate
    ? generalStatsDate.value
    : "2026-01-01";

  showLoader("Recalculando acierto y rentabilidad de partidos...");

  try {
    const res = await fetch(
      `/api/v1/analysis/recalculate-all?use_general_stats=${useGeneral}&threshold_date=${thresholdDate}&parallel=true`,
      { method: "POST" },
    );
    if (!res.ok) throw new Error("Error al recalcular");
  } catch (error) {
    console.error("Recalculate failed:", error);
  }

  await fetchGlobalStats();
}

async function triggerApplyBlacklistAndFetch() {
  showLoader("Aplicando blacklist actual a picks existentes...");

  try {
    const res = await fetch("/api/v1/analysis/apply-blacklist", {
      method: "POST",
    });
    if (!res.ok) throw new Error("Error al aplicar blacklist");
    const data = await res.json();
    alert(data.message || "Blacklist aplicada con éxito.");
  } catch (error) {
    console.error("Apply blacklist failed:", error);
    alert("Hubo un error al aplicar la blacklist.");
  }

  await fetchGlobalStats();
}

function handleDashboardGeneralStatsChange() {
  const useGeneralCheck = $("dashboard-use-general-stats");
  const generalStatsDate = $("dashboard-general-stats-date");
  if (useGeneralCheck) {
    localStorage.setItem("use_general_stats_system", useGeneralCheck.checked);
    if (generalStatsDate) {
      generalStatsDate.style.display = useGeneralCheck.checked
        ? "inline-block"
        : "none";
    }
  }
  triggerRecalculateAndFetch();
}

function handleDashboardGeneralStatsDateChange() {
  const generalStatsDate = $("dashboard-general-stats-date");
  if (generalStatsDate) {
    localStorage.setItem(
      "general_stats_threshold_date",
      generalStatsDate.value,
    );
  }
  triggerRecalculateAndFetch();
}

// Fetch stats from backend. Core stats are required; admin summary and
// anomalies are optional enrichments and never block the dashboard.
let fetchSeq = 0;
async function fetchGlobalStats() {
  const seq = ++fetchSeq;
  try {
    const p = buildDashboardParams();
    // Enrichments are slow (~20s each): start them now, render when they land.
    const enrich = (url, assign) =>
      fetch(url)
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null)
        .then((data) => {
          if (seq !== fetchSeq) return;
          assign(data);
          if (globalStatsData) renderDashboard();
        });
    adminSummary = undefined; // undefined = cargando, null = falló
    adminAnomalies = undefined;
    enrich(`/api/v1/admin/dashboard/summary${p.range}`, (d) => (adminSummary = d));
    enrich(`/api/v1/admin/stats/anomalies`, (d) => (adminAnomalies = d));

    const statsRes = await fetch(`/api/v1/stats/global${p.all}`);
    if (!statsRes.ok) throw new Error("Error al cargar estadísticas");
    const data = await statsRes.json();
    if (seq !== fetchSeq) return; // a newer request superseded this one
    globalStatsData = data;

    $("loader").style.display = "none";
    $("dashboard-content").style.display = "block";

    renderDashboard();
    if (!firstRenderDone) {
      firstRenderDone = true;
      // Entrance stagger runs once; later re-renders must not replay it.
      setTimeout(() => $("sx-body")?.classList.remove("sx-enter"), 1200);
    }
  } catch (error) {
    console.error(error);
    const loader = $("loader");
    if (loader) {
      loader.innerHTML = `<span class="sx-neg">❌ Error al cargar estadísticas. Por favor intenta de nuevo.</span>`;
    }
  }
}

// Switch between tabs
function switchCategory(category) {
  activeCategory = category;
  document.querySelectorAll(".tab-link[data-cat]").forEach((btn) => {
    btn.classList.toggle("tab-link--active", btn.dataset.cat === category);
  });
  renderDashboard();
}

function currentCategoryStats() {
  if (!globalStatsData) return null;
  return activeCategory === "global"
    ? globalStatsData
    : globalStatsData.category_stats?.[activeCategory] || null;
}

// Render/Update all dashboard components
function renderDashboard() {
  const currentStats = currentCategoryStats();
  if (!currentStats) return;
  const isGlobal = activeCategory === "global";

  renderDataHealth(currentStats, isGlobal);
  renderPerformance(currentStats, isGlobal);

  renderRankings(currentStats.best_leagues, "list-best-leagues", "🏆");
  renderRankings(currentStats.best_teams, "list-best-teams", "⚽");
  renderWorstMarkets(currentStats.worst_markets);
  renderSports();
  renderAnomalies();

  renderMarketChart(currentStats.best_markets);
  renderBucketsChart(currentStats.odds_buckets, currentStats.edge_buckets);
  renderConfidenceChart(currentStats.confidence_buckets);
  renderCalibrationChart();
  renderDailyProfitChart(currentStats.daily_profit_series || []);

  updateCapitalSimulator();
}

// ── Salud de los datos ─────────────────────────────────────────────
function renderDataHealth(cur, isGlobal) {
  const g = globalStatsData;
  const k = adminSummary?.kpis;
  const q = adminSummary?.quality;
  const scopeNote = " · todos los picks calculados";

  if (isGlobal) {
    const total = g.total_matches || 0;
    const resolved = g.total_matches_with_results || 0;
    const cov = total > 0 ? (resolved / total) * 100 : 0;
    setText("stat-total-matches", String(total));
    setText("stat-resolved-matches", `${resolved} con resultado`);
    $("bar-coverage").style.width = `${cov.toFixed(1)}%`;
    setText(
      "health-coverage-note",
      `Cobertura de resultados: ${cov.toFixed(1)}% · ${total - resolved} sin resultado`,
    );

    const exactPred = g.total_exact_scores_predicted || 0;
    setText("stat-exact-scores", String(g.total_exact_scores_hits || 0));
    setText(
      "stat-exact-ratio",
      `${exactPred > 0 ? ((g.total_exact_scores_hits / exactPred) * 100).toFixed(1) : "0.0"}% (${exactPred} predichos)`,
    );
  } else {
    setText("stat-total-matches", "-");
    setText("stat-resolved-matches", "N/A en esta categoría");
    $("bar-coverage").style.width = "0%";
    setText("health-coverage-note", "Cobertura solo disponible en Global");
    setText("stat-exact-scores", "-");
    setText("stat-exact-ratio", "Solo disponible en Global");
  }

  setText("stat-total-picks", String(cur.total_picks || 0));
  setText("stat-pending-picks", `${cur.total_pending || 0} pendientes`);

  // Outcome distribution bar (W / L / push / void / pending)
  // Same population as the "Picks evaluados" card (counted picks only).
  const hits = cur.total_hits || 0;
  const parts = [
    ["Ganados", hits, PALETTE.pos],
    ["Perdidos", Math.max((cur.total_picks || 0) - hits, 0), PALETTE.neg],
    ["Pendientes", cur.total_pending || 0, PALETTE.warn],
  ];
  const sum = parts.reduce((s, p) => s + (p[1] || 0), 0);
  $("bar-outcomes").innerHTML = parts
    .filter((p) => p[1] > 0)
    .map(
      (p) =>
        `<span title="${esc(p[0])}: ${p[1]}" style="width:${((p[1] / sum) * 100).toFixed(2)}%;background:${p[2]}"></span>`,
    )
    .join("");
  $("legend-outcomes").innerHTML = parts
    .filter((p) => p[1] > 0)
    .map(
      (p) =>
        `<span><i class="sx-dot" style="background:${p[2]}"></i>${esc(p[0])} ${p[1]}</span>`,
    )
    .join("");

  // Anomalies
  const anomEl = $("health-anomalies");
  if (adminAnomalies) {
    const n = adminAnomalies.total_anomalies || 0;
    const high = (adminAnomalies.anomalies || []).filter(
      (a) => a.severity === "high",
    ).length;
    anomEl.textContent = String(n);
    anomEl.classList.remove("sx-pos", "sx-neg", "sx-warn");
    anomEl.classList.add(n === 0 ? "sx-pos" : high > 0 ? "sx-neg" : "sx-warn");
    setText(
      "health-anomalies-sub",
      n === 0 ? "Sin inconsistencias" : `${high} de severidad alta`,
    );
  } else {
    anomEl.textContent = "-";
    setText(
      "health-anomalies-sub",
      adminAnomalies === undefined ? "Calculando..." : "No disponible",
    );
  }

  // Model quality
  const brierEl = $("health-brier");
  if (q && q.brier_score != null) {
    brierEl.textContent = q.brier_score.toFixed(4);
    brierEl.classList.remove("sx-pos", "sx-neg", "sx-warn");
    brierEl.classList.add(
      q.brier_score < 0.22 ? "sx-pos" : q.brier_score < 0.25 ? "sx-warn" : "sx-neg",
    );
    setText("health-brier-sub", `Menor es mejor (0.25 = azar)${scopeNote}`);
  } else {
    brierEl.textContent = "-";
    brierEl.classList.remove("sx-pos", "sx-neg", "sx-warn");
    setText(
      "health-brier-sub",
      adminSummary === undefined ? "Calculando..." : "Sin picks resueltos",
    );
  }

  const gapEl = $("health-model-gap");
  if (q) {
    gapEl.textContent = signed(q.actual_vs_expected_diff, 1, " pp");
    setTone(gapEl, q.actual_vs_expected_diff);
    setText(
      "health-model-gap-sub",
      `Modelo ${q.avg_model_prob.toFixed(1)}% vs. real ${(q.avg_model_prob + q.actual_vs_expected_diff).toFixed(1)}%${scopeNote}`,
    );
  } else {
    gapEl.textContent = "-";
    setTone(gapEl, 0);
    setText(
      "health-model-gap-sub",
      adminSummary === undefined ? "Calculando..." : "Sin datos del modelo",
    );
  }

  const clvEl = $("health-clv");
  if (k && k.avg_clv != null) {
    clvEl.textContent = signed(k.avg_clv, 2, "%");
    setTone(clvEl, k.avg_clv);
  } else {
    clvEl.textContent = "-";
    setTone(clvEl, 0);
  }
}

// ── Rendimiento ────────────────────────────────────────────────────
function renderPerformance(cur, isGlobal) {
  const accuracy = (isGlobal ? globalStatsData.global_accuracy : cur.accuracy) || 0;
  setText("stat-accuracy", `${accuracy.toFixed(1)}%`);
  setText(
    "stat-hits-ratio",
    `${cur.total_hits || 0} hits de ${cur.total_picks || 0}`,
  );

  const avgOdds = cur.avg_odds || 0;
  setText("stat-avg-odds", `@${avgOdds.toFixed(2)}`);
  setText(
    "stat-avg-winning-odds",
    `Ganadoras: @${(cur.avg_winning_odds || 0).toFixed(2)}`,
  );

  // Break-even vs real hit rate: a hit rate under break-even loses money
  const be = avgOdds > 1 ? 100 / avgOdds : 0;
  const beEl = $("kpi-breakeven");
  if (beEl) {
    beEl.textContent =
      be > 0
        ? `Break-even ${be.toFixed(1)}% · ${signed(accuracy - be, 1, " pp")}`
        : "Break-even: -";
    setTone(beEl, be > 0 ? accuracy - be : 0);
  }

  const totalProfit = cur.total_profit || 0;
  const profitEl = $("stat-total-profit");
  profitEl.textContent = `${signed(totalProfit)} u`;
  setTone(profitEl, totalProfit);

  const roi = cur.roi ?? 0;
  setText("stat-roi", `ROI (flat stake): ${Number(roi).toFixed(1)}%`);

  const breakdownEl = $("category-profit-breakdown");
  if (breakdownEl) {
    if (isGlobal && globalStatsData.category_stats) {
      breakdownEl.style.display = "block";
      const setB = (id, val) => {
        const el = $(id);
        el.textContent = `${signed(val)} u`;
        setTone(el, val);
      };
      setB(
        "prof-breakdown-pro",
        globalStatsData.category_stats.professional?.total_profit || 0,
      );
      setB(
        "prof-breakdown-und",
        globalStatsData.category_stats.underdog?.total_profit || 0,
      );
    } else {
      breakdownEl.style.display = "none";
    }
  }

  // Drawdown & best/worst day from the cumulative series
  const series = cur.daily_profit_series || [];
  let peak = 0;
  let maxDd = 0;
  let best = null;
  let worst = null;
  for (const d of series) {
    const cum = Number(d.cumulative) || 0;
    peak = Math.max(peak, cum);
    maxDd = Math.max(maxDd, peak - cum);
    const day = Number(d.daily) || 0;
    if (!best || day > best.v) best = { v: day, date: d.date };
    if (!worst || day < worst.v) worst = { v: day, date: d.date };
  }
  const ddEl = $("kpi-drawdown");
  ddEl.textContent = series.length ? `-${maxDd.toFixed(2)} u` : "-";
  ddEl.classList.remove("sx-pos", "sx-neg", "sx-warn");
  if (series.length && maxDd > 0) ddEl.classList.add("sx-neg");

  const bestEl = $("kpi-bestday");
  if (best && worst) {
    bestEl.innerHTML = `<span class="${tone(best.v)}">${signed(best.v)}</span> / <span class="${tone(worst.v)}">${signed(worst.v)}</span>`;
  } else {
    bestEl.textContent = "-";
  }
  setText("kpi-days-sub", `Días con picks resueltos: ${series.length}`);

  const k = adminSummary?.kpis;
  if (k && isGlobal) {
    const edge = adminSummary.quality.avg_edge ?? 0;
    const edgeEl = setText("kpi-edge", `${edge.toFixed(2)}%`);
    edgeEl.classList.toggle("sx-warn", edge > 50); // >50% medio = outliers en los datos
    setText(
      "kpi-kelly",
      edge > 50
        ? "Atípico: hay edges extremos, revisa anomalías"
        : `Kelly: ${(k.avg_kelly * 100).toFixed(2)}% del bankroll`,
    );
  } else {
    setText("kpi-edge", "-");
    setText("kpi-kelly", "Solo disponible en Global");
  }
}

// ── Listas ─────────────────────────────────────────────────────────
function rowHtml(name, meta, profit, roiVal) {
  const cls = profit >= 0 ? "sx-pos" : "sx-neg";
  return `
    <div class="sx-row">
      <div class="sx-row__main">
        <div class="sx-row__name" title="${esc(name)}">${esc(name)}</div>
        <div class="sx-row__meta">${meta}</div>
      </div>
      <div class="sx-row__val ${cls}">${signed(profit)} u<small>${signed(roiVal, 1, "%")}</small></div>
    </div>`;
}

function itemRoi(item) {
  return item.roi !== undefined
    ? item.roi
    : item.picks > 0
      ? (item.profit / item.picks) * 100
      : 0;
}

function renderRankings(items, containerId, emoji) {
  const container = $(containerId);
  if (!container) return;
  if (!items || items.length === 0) {
    container.innerHTML = `<div class="sx-none">Sin datos de rendimiento para esta categoría</div>`;
    return;
  }
  const topItems = [...items].sort((a, b) => b.profit - a.profit).slice(0, 10);
  container.innerHTML = topItems
    .map((item) =>
      rowHtml(
        `${emoji} ${item.name}`,
        `${item.hits}/${item.picks} aciertos (${item.accuracy.toFixed(1)}%)`,
        item.profit,
        itemRoi(item),
      ),
    )
    .join("");
}

function renderWorstMarkets(items) {
  const container = $("list-worst-markets");
  if (!container) return;
  const list = (items || []).filter((m) => m.profit < 0).slice(0, 8);
  if (!list.length) {
    container.innerHTML = `<div class="sx-none">Sin mercados con pérdidas</div>`;
    return;
  }
  container.innerHTML = list
    .map((m) =>
      rowHtml(
        m.name,
        `${m.hits}/${m.picks} aciertos (${m.accuracy.toFixed(1)}%)`,
        m.profit,
        itemRoi(m),
      ),
    )
    .join("");
}

function renderSports() {
  const container = $("list-sports");
  if (!container) return;
  const entries = Object.entries(globalStatsData?.sport_stats || {}).sort(
    (a, b) => (b[1].picks || 0) - (a[1].picks || 0),
  );
  if (!entries.length) {
    container.innerHTML = `<div class="sx-none">Sin datos por deporte</div>`;
    return;
  }
  const maxPicks = Math.max(...entries.map((e) => e[1].picks || 0), 1);
  container.innerHTML = entries
    .map(([sport, s]) => {
      const w = ((s.picks || 0) / maxPicks) * 100;
      return `
      <div class="sx-row" style="display:block">
        <div style="display:flex;justify-content:space-between;gap:.75rem">
          <span class="sx-row__name">${esc(sport)}</span>
          <span class="sx-row__val">${(s.accuracy || 0).toFixed(1)}%</span>
        </div>
        <div class="sx-bar" style="height:6px"><span style="width:${w.toFixed(1)}%;background:${PALETTE.accent}"></span></div>
        <div class="sx-row__meta" style="margin-top:.3rem">${s.hits || 0}/${s.picks || 0} aciertos</div>
      </div>`;
    })
    .join("");
}

function renderAnomalies() {
  const container = $("list-anomalies");
  if (!container) return;
  if (!adminAnomalies) {
    container.innerHTML = `<div class="sx-none">${adminAnomalies === undefined ? "Analizando integridad de datos..." : "No se pudo consultar la integridad de datos"}</div>`;
    setText("anomalies-hint", "");
    return;
  }
  const items = adminAnomalies.anomalies || [];
  setText("anomalies-hint", `${adminAnomalies.total_anomalies || 0} en total`);
  if (!items.length) {
    container.innerHTML = `<div class="sx-none sx-pos">✔ Sin anomalías detectadas</div>`;
    return;
  }
  const order = { high: 0, medium: 1, low: 2 };
  container.innerHTML = [...items]
    .sort((a, b) => (order[a.severity] ?? 3) - (order[b.severity] ?? 3))
    .slice(0, 30)
    .map((a) => {
      const sev = ["high", "medium", "low"].includes(a.severity)
        ? a.severity
        : "low";
      return `
      <div class="sx-row">
        <div class="sx-row__main">
          <div class="sx-row__name" title="${esc(a.match_title)}">${esc(a.match_title)}</div>
          <div class="sx-row__meta">${esc(a.anomaly_type)} · ${esc(a.description)}</div>
        </div>
        <span class="sx-sev sx-sev--${sev}">${esc(sev)}</span>
      </div>`;
    })
    .join("");
}

// ── Charts ─────────────────────────────────────────────────────────
function setEmpty(wrapId, empty) {
  const w = $(wrapId);
  if (w) w.dataset.empty = empty ? "true" : "false";
}

function baseOptions(extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: REDUCED_MOTION ? false : { duration: 300 },
    interaction: { mode: "index", intersect: false },
    ...extra,
  };
}
const tooltipStyle = {
  backgroundColor: "#0a0e14",
  titleColor: PALETTE.text,
  bodyColor: PALETTE.text2,
  borderColor: "rgba(148,163,184,0.2)",
  borderWidth: 1,
  padding: 10,
  cornerRadius: 10,
};
const axisTicks = { color: PALETTE.text2, font: { family: "Inter", size: 11 } };
const pctAxis = (extra = {}) => ({
  min: 0,
  max: 100,
  grid: { color: PALETTE.grid },
  border: { display: false },
  ticks: { ...axisTicks, callback: (v) => v + "%" },
  ...extra,
});
const catAxis = {
  grid: { display: false },
  border: { color: PALETTE.grid },
  ticks: axisTicks,
};

function renderMarketChart(bestMarkets) {
  if (marketChartInstance) marketChartInstance.destroy();
  marketChartInstance = null;
  const empty = !bestMarkets || bestMarkets.length === 0;
  setEmpty("wrap-market", empty);
  if (empty) return;

  const sorted = [...bestMarkets].sort((a, b) => b.picks - a.picks);
  const profitData = sorted.map((m) => m.profit);

  marketChartInstance = new Chart($("marketChart").getContext("2d"), {
    type: "bar",
    data: {
      labels: sorted.map((m) => m.name),
      datasets: [
        {
          label: "Acierto (%)",
          data: sorted.map((m) => m.accuracy),
          backgroundColor: "rgba(34, 211, 238, 0.7)",
          yAxisID: "yAccuracy",
          borderRadius: 6,
          barPercentage: 0.6,
        },
        {
          label: "Beneficio neto (u)",
          data: profitData,
          backgroundColor: profitData.map((p) =>
            p >= 0 ? "rgba(52, 211, 153, 0.75)" : "rgba(251, 113, 133, 0.75)",
          ),
          yAxisID: "yProfit",
          borderRadius: 6,
          barPercentage: 0.6,
        },
      ],
    },
    options: baseOptions({
      scales: {
        x: { ...catAxis, ticks: { ...axisTicks, maxRotation: 40 } },
        yAccuracy: { ...pctAxis(), type: "linear", position: "left" },
        yProfit: {
          type: "linear",
          position: "right",
          grid: { drawOnChartArea: false },
          border: { display: false },
          ticks: {
            ...axisTicks,
            callback: (v) => (v >= 0 ? "+" : "") + v + " u",
          },
        },
      },
      plugins: {
        legend: {
          labels: { color: PALETTE.text, boxWidth: 10, boxHeight: 10, usePointStyle: true, font: { family: "Inter" } },
        },
        tooltip: {
          ...tooltipStyle,
          callbacks: {
            afterBody: (ctx) => `Picks: ${sorted[ctx[0].dataIndex].picks}`,
          },
        },
      },
    }),
  });
}

function bucketChart(canvasId, wrapId, buckets, color, previous) {
  if (previous) previous.destroy();
  const empty = !buckets || buckets.length === 0;
  setEmpty(wrapId, empty);
  if (empty) return null;
  return new Chart($(canvasId).getContext("2d"), {
    type: "bar",
    data: {
      labels: buckets.map((b) => b.bucket),
      datasets: [
        {
          label: "Acierto (%)",
          data: buckets.map((b) => b.accuracy),
          backgroundColor: color,
          borderRadius: 6,
        },
      ],
    },
    options: baseOptions({
      scales: { x: catAxis, y: pctAxis() },
      plugins: {
        legend: { display: false },
        tooltip: {
          ...tooltipStyle,
          callbacks: {
            afterBody: (ctx) =>
              `Picks: ${buckets[ctx[0].dataIndex].count} · Cuota media @${(buckets[ctx[0].dataIndex].avg_odds || 0).toFixed(2)}`,
          },
        },
      },
    }),
  });
}

function renderBucketsChart(oddsBuckets, edgeBuckets) {
  oddsChartInstance = bucketChart(
    "oddsChart", "wrap-odds", oddsBuckets, "rgba(129, 140, 248, 0.75)", oddsChartInstance,
  );
  edgeChartInstance = bucketChart(
    "edgeChart", "wrap-edge", edgeBuckets, "rgba(251, 191, 36, 0.75)", edgeChartInstance,
  );
}

function renderConfidenceChart(confBuckets) {
  confChartInstance = bucketChart(
    "confChart", "wrap-conf", confBuckets, "rgba(34, 211, 238, 0.7)", confChartInstance,
  );
}

function renderCalibrationChart() {
  if (calibChartInstance) calibChartInstance.destroy();
  calibChartInstance = null;
  const bands = (adminSummary?.quality?.calibration_bands || []).filter(
    (b) => b.total_picks > 0,
  );
  setEmpty("wrap-calib", bands.length === 0);
  if (!bands.length) return;

  calibChartInstance = new Chart($("calibChart").getContext("2d"), {
    type: "bar",
    data: {
      labels: bands.map((b) => b.band),
      datasets: [
        {
          label: "Modelo (%)",
          data: bands.map((b) => b.avg_model_prob),
          backgroundColor: "rgba(148, 163, 184, 0.45)",
          borderRadius: 6,
        },
        {
          label: "Real (%)",
          data: bands.map((b) => b.actual_hit_rate),
          backgroundColor: bands.map((b) =>
            b.diff >= 0 ? "rgba(52, 211, 153, 0.8)" : "rgba(251, 113, 133, 0.8)",
          ),
          borderRadius: 6,
        },
      ],
    },
    options: baseOptions({
      scales: { x: catAxis, y: pctAxis() },
      plugins: {
        legend: {
          labels: { color: PALETTE.text, boxWidth: 10, boxHeight: 10, usePointStyle: true, font: { family: "Inter", size: 11 } },
        },
        tooltip: {
          ...tooltipStyle,
          callbacks: {
            afterBody: (ctx) => {
              const b = bands[ctx[0].dataIndex];
              return `Picks: ${b.total_picks} · Desv.: ${signed(b.diff, 1, " pp")}`;
            },
          },
        },
      },
    }),
  });
}

function renderDailyProfitChart(dailySeries) {
  if (dailyProfitChartInstance) dailyProfitChartInstance.destroy();
  dailyProfitChartInstance = null;
  const empty = !dailySeries || dailySeries.length === 0;
  setEmpty("wrap-daily", empty);
  if (empty) return;

  const chartSeries = [...dailySeries];
  if (chartSeries.length === 1) {
    chartSeries.unshift({ date: "Inicio", daily: 0, cumulative: 0 });
  }
  const labels = chartSeries.map((d) => {
    if (d.date === "Inicio") return "Inicio";
    const p = String(d.date).split("-");
    return p.length === 3 ? `${p[2]}/${p[1]}` : d.date;
  });
  const cumulative = chartSeries.map((d) => d.cumulative);
  const daily = chartSeries.map((d) => d.daily ?? 0);

  dailyProfitChartInstance = new Chart($("dailyProfitChart").getContext("2d"), {
    data: {
      labels,
      datasets: [
        {
          type: "line",
          label: "Acumulado (u)",
          data: cumulative,
          borderColor: PALETTE.accent,
          backgroundColor: "rgba(34, 211, 238, 0.1)",
          borderWidth: 2,
          fill: true,
          tension: 0.25,
          pointRadius: 2,
          pointHoverRadius: 5,
          pointBackgroundColor: PALETTE.accent,
          order: 1,
        },
        {
          type: "bar",
          label: "Día (u)",
          data: daily,
          backgroundColor: daily.map((v) =>
            v >= 0 ? "rgba(52, 211, 153, 0.5)" : "rgba(251, 113, 133, 0.5)",
          ),
          borderRadius: 3,
          order: 2,
        },
      ],
    },
    options: baseOptions({
      scales: {
        x: { ...catAxis, ticks: { ...axisTicks, maxTicksLimit: 14 } },
        y: {
          grid: { color: PALETTE.grid },
          border: { display: false },
          ticks: {
            ...axisTicks,
            callback: (v) => (v > 0 ? "+" : "") + v + " u",
          },
        },
      },
      plugins: {
        legend: {
          labels: { color: PALETTE.text, boxWidth: 10, boxHeight: 10, usePointStyle: true, font: { family: "Inter" } },
        },
        tooltip: {
          ...tooltipStyle,
          callbacks: {
            label: (c) => `${c.dataset.label}: ${signed(c.raw)} u`,
          },
        },
      },
    }),
  });
}

// ── Capital Simulator ──────────────────────────────────────────────
function updateCapitalSimulator() {
  const currentStats = currentCategoryStats();
  if (!currentStats) return;

  const totalProfitUnits = currentStats.total_profit || 0;
  const bankrollInput = $("sim-bankroll");
  const unitInput = $("sim-unit");
  if (!bankrollInput || !unitInput) return;

  const initialBankroll = parseFloat(bankrollInput.value) || 0;
  const unitValue = parseFloat(unitInput.value) || 0;
  const moneyProfit = totalProfitUnits * unitValue;

  const formatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  });
  $("sim-result").textContent = formatter.format(initialBankroll + moneyProfit);
  const profEl = $("sim-profit");
  profEl.textContent = `${moneyProfit >= 0 ? "+" : ""}${formatter.format(moneyProfit)}`;
  profEl.style.color = moneyProfit >= 0 ? PALETTE.pos : PALETTE.neg;
}

// ── Polling for external match results (pushed by browser extensions) ──
function startResultPolling() {
  const POLL_INTERVAL = 3000; // ms

  async function checkResult() {
    try {
      const res = await fetch("/api/v1/result");
      if (res.ok) {
        const data = await res.json();
        if (data.pending && data.payload) {
          showResultBanner(data.payload);
          // Reload dashboard stats to reflect the newly updated match result
          fetchGlobalStats();
        }
      }
    } catch (_) {
      // silently ignore network errors
    }
    setTimeout(checkResult, POLL_INTERVAL);
  }

  function showResultBanner(payload) {
    $("result-push-banner")?.remove();

    const home = payload.home_team || payload.home?.name || "";
    const away = payload.away_team || payload.away?.name || "";
    const hScore =
      payload.final_score_home !== undefined ? payload.final_score_home : "?";
    const aScore =
      payload.final_score_away !== undefined ? payload.final_score_away : "?";

    const banner = document.createElement("div");
    banner.id = "result-push-banner";
    banner.className = "sx-toast";
    banner.setAttribute("role", "status");
    banner.innerHTML = `
      <span style="font-size:1.4rem">🏆</span>
      <div>
        <div class="sx-kpi__label">Resultado registrado</div>
        <div style="margin-top:2px">${esc(home)} <strong>${esc(hScore)} - ${esc(aScore)}</strong> ${esc(away)}</div>
      </div>
      <button type="button" aria-label="Cerrar">✕</button>
    `;
    banner.querySelector("button").addEventListener("click", () => banner.remove());
    document.body.appendChild(banner);
    setTimeout(() => banner.remove(), 8000);
  }

  setTimeout(checkResult, 2000);
}

// Generar y descargar reporte detallado de Excel
function downloadExcelReport() {
  window.location.href = `/api/v1/report/excel${getDashboardDateParams()}`;
}
