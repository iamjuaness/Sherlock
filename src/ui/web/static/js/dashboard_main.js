// Sherlock - Main Dashboard script
let globalStatsData = null;
let activeCategory = "global"; // 'global', 'professional', 'underdog'

// Chart instances
let marketChartInstance = null;
let oddsChartInstance = null;
let edgeChartInstance = null;
let dailyProfitChartInstance = null;

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  // Sync checkbox with localStorage
  const useStakeCheck = document.getElementById("dashboard-use-stake");
  if (useStakeCheck) {
    const saved = localStorage.getItem("use_stake_system");
    if (saved !== null) {
      useStakeCheck.checked = saved === "true";
    } else {
      localStorage.setItem("use_stake_system", "true");
    }
  }

  const useGeneralCheck = document.getElementById(
    "dashboard-use-general-stats",
  );
  const generalStatsDate = document.getElementById(
    "dashboard-general-stats-date",
  );
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
        generalStatsDate.value = "2026-07-01";
        localStorage.setItem("general_stats_threshold_date", "2026-07-01");
      }
      generalStatsDate.style.display = useGeneralCheck.checked
        ? "inline-block"
        : "none";
    }
  }

  fetchGlobalStats();
  startResultPolling();

  // Setup Simulator button
  document
    .getElementById("btn-simulate")
    .addEventListener("click", updateCapitalSimulator);
});

// Helper to get selected date range parameters for dashboard
function getDashboardDateParams() {
  const range = document.getElementById("dashboard-date-range")
    ? document.getElementById("dashboard-date-range").value
    : "all";
  let dateFrom = "";
  let dateTo = "";

  // Helper que formatea una fecha local como YYYY-MM-DDTHH:mm:ss
  function formatLocalDateTime(date, time = "00:00:00") {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}T${time}`;
  }

  if (range === "today") {
    const today = new Date();
    dateFrom = formatLocalDateTime(today, "00:00:00");
    dateTo = formatLocalDateTime(today, "23:59:59");
  } else if (range === "7days") {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    dateFrom = formatLocalDateTime(d, "00:00:00");
  } else if (range === "3days") {
    const d = new Date();
    d.setDate(d.getDate() - 3);
    dateFrom = formatLocalDateTime(d, "00:00:00");
  } else if (range === "30days") {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    dateFrom = formatLocalDateTime(d, "00:00:00");
  } else if (range === "custom") {
    const fromVal = document.getElementById("dashboard-date-from")
      ? document.getElementById("dashboard-date-from").value
      : "";
    const toVal = document.getElementById("dashboard-date-to")
      ? document.getElementById("dashboard-date-to").value
      : "";
    if (fromVal) dateFrom = `${fromVal}T00:00:00`;
    if (toVal) dateTo = `${toVal}T23:59:59`;
  }

  let params = [];
  if (dateFrom) params.push(`date_from=${encodeURIComponent(dateFrom)}`);
  if (dateTo) params.push(`date_to=${encodeURIComponent(dateTo)}`);

  const useStakeCheck = document.getElementById("dashboard-use-stake");
  if (useStakeCheck && useStakeCheck.checked) {
    params.push("use_stake=true");
  }

  const useGeneralCheck = document.getElementById(
    "dashboard-use-general-stats",
  );
  if (useGeneralCheck && useGeneralCheck.checked) {
    params.push("use_general_stats=true");
  }

  return params.length > 0 ? "?" + params.join("&") : "";
}

function handleDashboardDateRangeChange() {
  const range = document.getElementById("dashboard-date-range").value;
  const customInputs = document.getElementById("dashboard-custom-date-inputs");
  if (customInputs) {
    customInputs.style.display = range === "custom" ? "flex" : "none";
  }
  reloadDashboardStats();
}

async function reloadDashboardStats() {
  const useStakeCheck = document.getElementById("dashboard-use-stake");
  if (useStakeCheck) {
    localStorage.setItem("use_stake_system", useStakeCheck.checked);
  }
  const useGeneralCheck = document.getElementById(
    "dashboard-use-general-stats",
  );
  if (useGeneralCheck) {
    localStorage.setItem("use_general_stats_system", useGeneralCheck.checked);
  }
  await fetchGlobalStats();
}

async function triggerRecalculateAndFetch() {
  const useGeneralCheck = document.getElementById(
    "dashboard-use-general-stats",
  );
  const generalStatsDate = document.getElementById(
    "dashboard-general-stats-date",
  );
  const useGeneral = useGeneralCheck ? useGeneralCheck.checked : false;
  const thresholdDate = generalStatsDate
    ? generalStatsDate.value
    : "2026-07-01";

  const loader = document.getElementById("loader");
  const content = document.getElementById("dashboard-content");
  if (loader) {
    loader.style.display = "flex";
    loader.innerHTML =
      '<div class="spinner"></div><span>Recalculando acierto y rentabilidad de partidos...</span>';
  }
  if (content) {
    content.style.display = "none";
  }

  try {
    const res = await fetch(
      `/api/v1/analysis/recalculate-all?use_general_stats=${useGeneral}&threshold_date=${thresholdDate}`,
      {
        method: "POST",
      },
    );
    if (!res.ok) throw new Error("Error al recalcular");
  } catch (error) {
    console.error("Recalculate failed:", error);
  }

  await fetchGlobalStats();
}

async function triggerApplyBlacklistAndFetch() {
  const loader = document.getElementById("loader");
  const content = document.getElementById("dashboard-content");
  if (loader) {
    loader.style.display = "flex";
    loader.innerHTML =
      '<div class="spinner"></div><span>Aplicando blacklist actual a picks existentes...</span>';
  }
  if (content) {
    content.style.display = "none";
  }

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
  const useGeneralCheck = document.getElementById(
    "dashboard-use-general-stats",
  );
  const generalStatsDate = document.getElementById(
    "dashboard-general-stats-date",
  );
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
  const generalStatsDate = document.getElementById(
    "dashboard-general-stats-date",
  );
  if (generalStatsDate) {
    localStorage.setItem(
      "general_stats_threshold_date",
      generalStatsDate.value,
    );
  }
  triggerRecalculateAndFetch();
}

// Fetch stats from backend
async function fetchGlobalStats() {
  try {
    const queryParams = getDashboardDateParams();
    const res = await fetch(`/api/v1/stats/global${queryParams}`);
    if (!res.ok) throw new Error("Error al cargar estadísticas");
    globalStatsData = await res.json();

    // Hide loader, show content
    document.getElementById("loader").style.display = "none";
    document.getElementById("dashboard-content").style.display = "block";

    renderDashboard();
  } catch (error) {
    console.error(error);
    const loader = document.getElementById("loader");
    if (loader) {
      loader.innerHTML = `<span style="color: var(--red);">❌ Error al cargar estadísticas. Por favor intenta de nuevo.</span>`;
    }
  }
}

// Switch between tabs
function switchCategory(category) {
  activeCategory = category;

  // Update active tab styles
  document.querySelectorAll(".tab-link").forEach((btn) => {
    btn.classList.remove("tab-link--active");
  });

  // Find which tab button was clicked
  const tabIndex = {
    global: 0,
    professional: 1,
    underdog: 2,
  }[category];

  document
    .querySelectorAll(".tab-link")
    [tabIndex].classList.add("tab-link--active");

  renderDashboard();
}

// Render/Update all dashboard components
function renderDashboard() {
  if (!globalStatsData) return;

  // Get relevant dataset
  let currentStats = null;
  if (activeCategory === "global") {
    currentStats = globalStatsData;
  } else {
    currentStats = globalStatsData.category_stats?.[activeCategory];
  }

  if (!currentStats) return;

  // 1. Fill Card Stats
  if (activeCategory === "global") {
    document.getElementById("stat-total-matches").textContent =
      globalStatsData.total_matches || "0";
    document.getElementById("stat-resolved-matches").textContent =
      `${globalStatsData.total_matches_with_results || 0} resueltos`;

    document.getElementById("stat-exact-scores").textContent =
      `${globalStatsData.total_exact_scores_hits || 0}`;
    const exactRate =
      globalStatsData.total_exact_scores_predicted > 0
        ? (
            (globalStatsData.total_exact_scores_hits /
              globalStatsData.total_exact_scores_predicted) *
            100
          ).toFixed(1)
        : "0.0";
    document.getElementById("stat-exact-ratio").textContent =
      `${exactRate}% (${globalStatsData.total_exact_scores_predicted || 0} predichos)`;
  } else {
    // For specific categories, we don't have total_matches directly, so we adapt card labels
    document.getElementById("stat-total-matches").textContent = "-";
    document.getElementById("stat-resolved-matches").textContent =
      "N/A en esta categoría";

    document.getElementById("stat-exact-scores").textContent = "-";
    document.getElementById("stat-exact-ratio").textContent =
      "Solo disponible en Global";
  }

  // Common stats cards
  document.getElementById("stat-total-picks").textContent =
    currentStats.total_picks || "0";
  document.getElementById("stat-pending-picks").textContent =
    `${currentStats.total_pending || 0} pendientes`;

  const accuracy =
    (activeCategory === "global"
      ? globalStatsData.global_accuracy
      : currentStats.accuracy) || 0;
  document.getElementById("stat-accuracy").textContent =
    `${accuracy.toFixed(1)}%`;

  const totalResolvedPicks = currentStats.total_picks || 0;
  const totalHits = currentStats.total_hits || 0;
  document.getElementById("stat-hits-ratio").textContent =
    `${totalHits} hits de ${totalResolvedPicks}`;

  document.getElementById("stat-avg-odds").textContent =
    `@${(currentStats.avg_odds || 0).toFixed(2)}`;
  document.getElementById("stat-avg-winning-odds").textContent =
    `Ganadoras: @${(currentStats.avg_winning_odds || 0).toFixed(2)}`;

  // Total profit stats
  const totalProfit =
    (activeCategory === "global"
      ? globalStatsData.total_profit
      : currentStats.total_profit) || 0;
  const profitEl = document.getElementById("stat-total-profit");
  profitEl.textContent = `${totalProfit > 0 ? "+" : ""}${totalProfit.toFixed(2)} u`;
  profitEl.style.color =
    totalProfit > 0
      ? "var(--green)"
      : totalProfit < 0
        ? "var(--red)"
        : "var(--text-primary)";

  const roi =
    (activeCategory === "global" ? globalStatsData.roi : currentStats.roi) ?? 0;
  document.getElementById("stat-roi").textContent =
    `ROI (flat stake): ${Number(roi).toFixed(1)}%`;

  // Category breakdown display logic
  const breakdownEl = document.getElementById("category-profit-breakdown");
  if (breakdownEl) {
    if (activeCategory === "global" && globalStatsData.category_stats) {
      breakdownEl.style.display = "block";
      const proProf =
        globalStatsData.category_stats.professional?.total_profit || 0;
      const undProf =
        globalStatsData.category_stats.underdog?.total_profit || 0;
      const hcProf =
        globalStatsData.category_stats.high_confidence?.total_profit || 0;

      const setBreakdownStyle = (el, val) => {
        el.textContent = `${val > 0 ? "+" : ""}${val.toFixed(2)} u`;
        el.style.color =
          val > 0
            ? "var(--green)"
            : val < 0
              ? "var(--red)"
              : "var(--text-muted)";
      };

      setBreakdownStyle(document.getElementById("prof-breakdown-pro"), proProf);
      setBreakdownStyle(document.getElementById("prof-breakdown-und"), undProf);
    } else {
      breakdownEl.style.display = "none";
    }
  }

  // 2. Render Rankings (Ligas y Equipos)
  renderRankings(currentStats.best_leagues, "list-best-leagues", "🏆");
  renderRankings(currentStats.best_teams, "list-best-teams", "⚽");

  // 3. Render Charts
  renderMarketChart(currentStats.best_markets);
  renderBucketsChart(currentStats.odds_buckets, currentStats.edge_buckets);

  // Daily profit chart
  const dailySeries =
    activeCategory === "global"
      ? globalStatsData.daily_profit_series
      : currentStats.daily_profit_series || [];
  renderDailyProfitChart(dailySeries);

  // 4. Update simulator if there's data
  updateCapitalSimulator();
}

// Render rank lists (leagues/teams)
function renderRankings(items, containerId, emoji) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!items || items.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem; text-align: center;">Sin datos de rendimiento para esta categoría</div>`;
    return;
  }

  // Sort by profit desc, take top 5
  const topItems = [...items].sort((a, b) => b.profit - a.profit).slice(0, 5);

  container.innerHTML = topItems
    .map((item) => {
      const profitClass =
        item.profit >= 0 ? "profit--positive" : "profit--negative";
      const profitSign = item.profit >= 0 ? "+" : "";
      return `
      <div class="ranking-item">
        <div class="ranking-item__info">
          <span class="ranking-item__name">${emoji} ${item.name}</span>
          <span class="ranking-item__stats">${item.hits}/${item.picks} aciertos (${item.accuracy.toFixed(1)}%)</span>
        </div>
        <div class="ranking-item__profit ${profitClass}">
          ${profitSign}${item.profit.toFixed(2)} u
        </div>
      </div>
    `;
    })
    .join("");
}

// Render Markets bar chart
function renderMarketChart(bestMarkets) {
  const ctx = document.getElementById("marketChart").getContext("2d");

  if (marketChartInstance) {
    marketChartInstance.destroy();
  }

  if (!bestMarkets || bestMarkets.length === 0) {
    ctx.clearRect(0, 0, 400, 300);
    return;
  }

  // Sort by picks or profit
  const sortedMarkets = [...bestMarkets].sort((a, b) => b.picks - a.picks);
  const labels = sortedMarkets.map((m) => m.name);
  const accuracyData = sortedMarkets.map((m) => m.accuracy);
  const profitData = sortedMarkets.map((m) => m.profit);

  marketChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Acierto (%)",
          data: accuracyData,
          backgroundColor: "rgba(99, 102, 241, 0.65)",
          borderColor: "#6366f1",
          borderWidth: 1,
          yAxisID: "yAccuracy",
          borderRadius: 4,
          barPercentage: 0.5,
        },
        {
          label: "Beneficio neto (Unidades)",
          data: profitData,
          backgroundColor: profitData.map((p) =>
            p >= 0 ? "rgba(16, 185, 129, 0.65)" : "rgba(239, 68, 68, 0.65)",
          ),
          borderColor: profitData.map((p) => (p >= 0 ? "#10b981" : "#ef4444")),
          borderWidth: 1,
          yAxisID: "yProfit",
          borderRadius: 4,
          barPercentage: 0.5,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#94a3b8", font: { family: "Inter", size: 10 } },
        },
        yAccuracy: {
          type: "linear",
          position: "left",
          min: 0,
          max: 100,
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: {
            color: "#94a3b8",
            callback: (value) => value + "%",
            font: { family: "Inter" },
          },
          title: {
            display: true,
            text: "Tasa de Acierto",
            color: "#94a3b8",
            font: { family: "Inter", weight: "bold" },
          },
        },
        yProfit: {
          type: "linear",
          position: "right",
          grid: { drawOnChartArea: false },
          ticks: {
            color: "#94a3b8",
            callback: (value) => (value >= 0 ? "+" : "") + value + " u",
            font: { family: "Inter" },
          },
          title: {
            display: true,
            text: "Beneficio Neto",
            color: "#94a3b8",
            font: { family: "Inter", weight: "bold" },
          },
        },
      },
      plugins: {
        legend: {
          labels: {
            color: "#f8fafc",
            font: { family: "Inter", weight: "500" },
          },
        },
        tooltip: {
          backgroundColor: "#090e1a",
          titleFont: { family: "Inter", weight: "bold" },
          bodyFont: { family: "Inter" },
          borderColor: "rgba(255, 255, 255, 0.1)",
          borderWidth: 1,
        },
      },
    },
  });
}

// Render Odds and Edge buckets charts
function renderBucketsChart(oddsBuckets, edgeBuckets) {
  // 1. Odds chart
  const ctxOdds = document.getElementById("oddsChart").getContext("2d");
  if (oddsChartInstance) oddsChartInstance.destroy();

  if (oddsBuckets && oddsBuckets.length > 0) {
    const oddsLabels = oddsBuckets.map((b) => b.bucket);
    const oddsAcc = oddsBuckets.map((b) => b.accuracy);
    const oddsCount = oddsBuckets.map((b) => b.count);

    oddsChartInstance = new Chart(ctxOdds, {
      type: "bar",
      data: {
        labels: oddsLabels,
        datasets: [
          {
            label: "Acierto (%)",
            data: oddsAcc,
            backgroundColor: "rgba(59, 130, 246, 0.6)",
            borderColor: "#3b82f6",
            borderWidth: 1.5,
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            grid: { color: "rgba(255,255,255,0.03)" },
            ticks: { color: "#94a3b8" },
          },
          y: {
            min: 0,
            max: 100,
            grid: { color: "rgba(255,255,255,0.05)" },
            ticks: { color: "#94a3b8", callback: (v) => v + "%" },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterBody: (context) => {
                const idx = context[0].dataIndex;
                return `Picks: ${oddsCount[idx]}`;
              },
            },
          },
        },
      },
    });
  }

  // 2. Edge chart
  const ctxEdge = document.getElementById("edgeChart").getContext("2d");
  if (edgeChartInstance) edgeChartInstance.destroy();

  if (edgeBuckets && edgeBuckets.length > 0) {
    const edgeLabels = edgeBuckets.map((b) => b.bucket);
    const edgeAcc = edgeBuckets.map((b) => b.accuracy);
    const edgeCount = edgeBuckets.map((b) => b.count);

    edgeChartInstance = new Chart(ctxEdge, {
      type: "bar",
      data: {
        labels: edgeLabels,
        datasets: [
          {
            label: "Acierto (%)",
            data: edgeAcc,
            backgroundColor: "rgba(245, 158, 11, 0.6)",
            borderColor: "#f59e0b",
            borderWidth: 1.5,
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            grid: { color: "rgba(255,255,255,0.03)" },
            ticks: { color: "#94a3b8" },
          },
          y: {
            min: 0,
            max: 100,
            grid: { color: "rgba(255,255,255,0.05)" },
            ticks: { color: "#94a3b8", callback: (v) => v + "%" },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterBody: (context) => {
                const idx = context[0].dataIndex;
                return `Picks: ${edgeCount[idx]}`;
              },
            },
          },
        },
      },
    });
  }
}

// Render Daily Profit Line Chart
function renderDailyProfitChart(dailySeries) {
  const ctx = document.getElementById("dailyProfitChart").getContext("2d");

  if (dailyProfitChartInstance) {
    dailyProfitChartInstance.destroy();
  }

  if (!dailySeries || dailySeries.length === 0) {
    ctx.clearRect(0, 0, 400, 300);
    return;
  }

  let chartSeries = [...dailySeries];
  if (chartSeries.length === 1) {
    chartSeries.unshift({
      date: "Inicio",
      daily: 0,
      cumulative: 0,
    });
  }

  const labels = chartSeries.map((d) => {
    if (d.date === "Inicio") return "Inicio";
    // Format YYYY-MM-DD to DD/MM
    const p = d.date.split("-");
    if (p.length === 3) return `${p[2]}/${p[1]}`;
    return d.date;
  });
  const dataPoints = chartSeries.map((d) => d.cumulative);

  dailyProfitChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Unidades Netas Acumuladas",
          data: dataPoints,
          borderColor: "#6366f1",
          backgroundColor: "rgba(99, 102, 241, 0.1)",
          borderWidth: 2,
          fill: true,
          tension: 0.2, // slight curve
          pointBackgroundColor: "#1e293b",
          pointBorderColor: "#6366f1",
          pointBorderWidth: 2,
          pointRadius: 3,
          pointHoverRadius: 5,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.05)" },
          ticks: { color: "#94a3b8", maxTicksLimit: 12 },
        },
        y: {
          grid: { color: "rgba(255,255,255,0.1)" },
          ticks: {
            color: "#94a3b8",
            callback: (v) => (v > 0 ? "+" : "") + v + " u",
          },
          // Ensure zero line is clearly visible
          border: {
            display: true,
            dash: [4, 4],
            color: "rgba(255,255,255,0.2)",
          },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#090e1a",
          titleFont: { family: "Inter", weight: "bold" },
          callbacks: {
            label: (context) => {
              const val = context.raw;
              return `Acumulado: ${val > 0 ? "+" : ""}${val.toFixed(2)} unidades`;
            },
          },
        },
      },
    },
  });
}

// Capital Simulator Logic
function updateCapitalSimulator() {
  if (!globalStatsData) return;

  let currentStats = null;
  if (activeCategory === "global") {
    currentStats = globalStatsData;
  } else {
    currentStats = globalStatsData.category_stats?.[activeCategory];
  }

  if (!currentStats) return;

  const totalProfitUnits =
    (activeCategory === "global"
      ? globalStatsData.total_profit
      : currentStats.total_profit) || 0;

  const bankrollInput = document.getElementById("sim-bankroll");
  const unitInput = document.getElementById("sim-unit");

  if (!bankrollInput || !unitInput) return;

  const initialBankroll = parseFloat(bankrollInput.value) || 0;
  const unitValue = parseFloat(unitInput.value) || 0;

  const moneyProfit = totalProfitUnits * unitValue;
  const finalBankroll = initialBankroll + moneyProfit;

  // Format as currency
  const formatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  });

  const resEl = document.getElementById("sim-result");
  const profEl = document.getElementById("sim-profit");

  resEl.textContent = formatter.format(finalBankroll);
  profEl.textContent = `${moneyProfit >= 0 ? "+" : ""}${formatter.format(moneyProfit)}`;

  profEl.style.color = moneyProfit >= 0 ? "var(--green)" : "var(--red)";
}

// Polling for external match results (pushed by browser extensions)
function startResultPolling() {
  const POLL_INTERVAL = 3000; // ms

  async function checkResult() {
    try {
      const res = await fetch("/api/v1/result");
      if (!res.ok) return;
      const data = await res.json();
      if (data.pending && data.payload) {
        const payload = data.payload;
        showResultBanner(payload);

        // Reload dashboard stats to reflect the newly updated match result in DB!
        fetchGlobalStats();
      }
    } catch (_) {
      // silently ignore network errors
    }
    setTimeout(checkResult, POLL_INTERVAL);
  }

  function showResultBanner(payload) {
    let existing = document.getElementById("result-push-banner");
    if (existing) existing.remove();

    const home = payload.home_team || payload.home?.name || "";
    const away = payload.away_team || payload.away?.name || "";
    const hScore =
      payload.final_score_home !== undefined ? payload.final_score_home : "?";
    const aScore =
      payload.final_score_away !== undefined ? payload.final_score_away : "?";

    const banner = document.createElement("div");
    banner.id = "result-push-banner";
    banner.style.cssText = `
      position: fixed; bottom: 1.5rem; left: 1.5rem; z-index: 9999;
      background: linear-gradient(135deg, #3b82f6, #1d4ed8);
      color: #fff; padding: 1rem 1.5rem; border-radius: 12px;
      box-shadow: 0 8px 32px rgba(59,130,246,0.35);
      font-size: 0.9rem; font-weight: 600; display: flex; align-items: center; gap: 0.75rem;
      animation: slideInLeft 0.35s ease;
    `;
    banner.innerHTML = `
      <span style="font-size:1.4rem">🏆</span>
      <div>
        <div style="font-size:0.75rem; opacity:0.8; text-transform:uppercase;">Resultado Registrado</div>
        <div style="font-size:0.88rem; margin-top:2px;">
          ${home} <strong>${hScore} - ${aScore}</strong> ${away}
        </div>
      </div>
      <button onclick="this.parentElement.remove()" style="background:none;border:none;color:#fff;font-size:1.1rem;cursor:pointer;margin-left:0.5rem;">✕</button>
    `;

    // Add slideInLeft animation style dynamically if not defined
    if (!document.getElementById("slide-animation-style")) {
      const style = document.createElement("style");
      style.id = "slide-animation-style";
      style.innerHTML = `
        @keyframes slideInLeft {
          from { transform: translateX(-100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `;
      document.head.appendChild(style);
    }

    document.body.appendChild(banner);
    setTimeout(() => {
      if (banner && banner.parentElement) banner.remove();
    }, 8000);
  }

  setTimeout(checkResult, 2000);
}

// Generar y descargar reporte detallado de Excel
function downloadExcelReport() {
  const queryParams = getDashboardDateParams();
  window.location.href = `/api/v1/report/excel${queryParams}`;
}
