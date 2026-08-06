// leagues.js - Control de la sección de ligas en Sherlock
let leaguesData = [];
let activeLeague = null;
let activeView = "matches";
let visibleMatchesLimit = 50;
const MAX_STAKE = 3;
const MIN_STAKE = 1;

function switchView(view) {
  activeView = view;
  const tabMatches = document.getElementById("tab-matches");
  const tabMarkets = document.getElementById("tab-markets");
  const tabParams = document.getElementById("tab-params");
  const matchesList = document.getElementById("matches-list");
  const paramsPanel = document.getElementById("params-panel");

  [tabMatches, tabMarkets, tabParams].forEach(
    (t) => t && t.classList.remove("active"),
  );

  if (view === "params") {
    tabParams && tabParams.classList.add("active");
    if (matchesList) matchesList.style.display = "none";
    if (paramsPanel) paramsPanel.style.display = "block";
    loadLeagueParams();
    return;
  }

  if (matchesList) matchesList.style.display = "block";
  if (paramsPanel) paramsPanel.style.display = "none";

  if (view === "matches") {
    tabMatches && tabMatches.classList.add("active");
  } else {
    tabMarkets && tabMarkets.classList.add("active");
  }
  renderFilteredMatches();
}

document.addEventListener("DOMContentLoaded", () => {
  // Signal active state to backend so result pushing is enabled in leagues view
  fetch("/api/v1/leagues/active-state?active=true", { method: "POST" }).catch(
    () => {},
  );

  // Sync checkbox with localStorage
  const useStakeCheck = document.getElementById("leagues-use-stake");
  if (useStakeCheck) {
    const saved = localStorage.getItem("use_stake_system");
    if (saved !== null) {
      useStakeCheck.checked = saved === "true";
    } else {
      localStorage.setItem("use_stake_system", "true");
    }
  }
  fetchLeagues();
});

async function fetchLeagues() {
  try {
    const useStake = localStorage.getItem("use_stake_system") === "true";
    const res = await fetch(`/api/v1/stats/leagues?use_stake=${useStake}`);
    if (!res.ok) throw new Error("Error al cargar ligas");
    leaguesData = await res.json();

    // Sort leagues by profit desc
    leaguesData.sort((a, b) => b.total_profit - a.total_profit);

    document.getElementById("leagues-loader").style.display = "none";
    document.getElementById("leagues-content").style.display = "grid";

    renderLeaguesList();

    // Select first league by default if any
    if (leaguesData.length > 0) {
      selectLeague(leaguesData[0].name);
    }
  } catch (error) {
    console.error(error);
    document.getElementById("leagues-loader").innerHTML =
      `<span style="color: var(--red);">❌ Error al cargar ligas. Intenta de nuevo.</span>`;
  }
}

function renderLeaguesList() {
  const container = document.getElementById("leagues-list");
  if (!container) return;

  if (leaguesData.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.9rem; text-align: center; padding: 1rem;">No se encontraron competiciones.</div>`;
    return;
  }

  container.innerHTML = leaguesData
    .map((league) => {
      const activeClass =
        activeLeague === league.name ? "league-list-item--active" : "";
      const pendingClass = league.has_pending_matches
        ? "league-list-item--pending"
        : "";
      const profitClass =
        league.total_profit >= 0 ? "profit--positive" : "profit--negative";
      const profitSign = league.total_profit >= 0 ? "+" : "";
      return `
      <div class="league-list-item ${activeClass} ${pendingClass}" onclick="selectLeague('${escapeAttr(league.name)}')">
        <span class="league-list-item__name" title="${escapeHtml(league.name)}">🏆 ${escapeHtml(league.name)}</span>
        <span class="league-list-item__profit ${profitClass}">${profitSign}${league.total_profit.toFixed(2)}u</span>
      </div>
    `;
    })
    .join("");
}

let activeSeason = "all";
let currentMatchesCache = [];

function selectLeague(name) {
  activeLeague = name;
  activeSeason = "all";
  visibleMatchesLimit = 50;
  renderLeaguesList();

  const leagueInfo = leaguesData.find((l) => l.name === name);
  if (!leagueInfo) return;

  // Render stats DIRECTAMENTE desde leaguesData (backend)
  document.getElementById("selected-league-name").textContent = leagueInfo.name;
  document.getElementById("lbl-total-matches").textContent =
    leagueInfo.total_matches;
  document.getElementById("lbl-total-picks").textContent =
    leagueInfo.total_picks;
  document.getElementById("lbl-accuracy").textContent =
    `${leagueInfo.accuracy}%`;

  const profitEl = document.getElementById("lbl-profit");
  profitEl.textContent = `${leagueInfo.total_profit >= 0 ? "+" : ""}${leagueInfo.total_profit.toFixed(2)}u`;
  profitEl.style.color =
    leagueInfo.total_profit >= 0 ? "var(--green)" : "var(--red)";

  fetchMatchesForLeague(name);
}

async function fetchMatchesForLeague(name) {
  const matchesContainer = document.getElementById("matches-list");
  if (!matchesContainer) return;

  matchesContainer.innerHTML = `<div class="dashboard-loader"><div class="spinner"></div><span>Cargando partidos...</span></div>`;

  try {
    const useStake = localStorage.getItem("use_stake_system") === "true";
    const res = await fetch(
      `/api/v1/analysis?competition=${encodeURIComponent(name)}&use_stake=${useStake}`,
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    currentMatchesCache = await res.json();

    // Populate Season selector dropdown
    populateSeasonDropdown();

    renderFilteredMatches();
  } catch (error) {
    console.error("Error cargando partidos:", error);
    matchesContainer.innerHTML = `<div style="color: var(--red); padding: 2rem; text-align: center;">❌ Error al cargar partidos: ${escapeHtml(error.message)}</div>`;
  }
}

function populateSeasonDropdown() {
  const select = document.getElementById("selected-season");
  const container = document.getElementById("season-filter-card");
  if (!select || !container) return;

  // Extract all distinct season_years from matches payload
  const seasons = new Set();
  currentMatchesCache.forEach((m) => {
    let sYear = null;
    if (m.payload) {
      try {
        const p =
          typeof m.payload === "string" ? JSON.parse(m.payload) : m.payload;
        sYear = p.season_year || p.season;
      } catch (e) {}
    }
    if (sYear) {
      seasons.add(String(sYear));
    }
  });

  if (seasons.size > 0) {
    container.style.display = "block";

    // Sort seasons descending (e.g. 2026, 2025...)
    const sortedSeasons = Array.from(seasons).sort((a, b) =>
      b.localeCompare(a),
    );

    let html = '<option value="all">Todas las temporadas</option>';
    sortedSeasons.forEach((s) => {
      html += `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`;
    });
    select.innerHTML = html;
    select.value = activeSeason;
  } else {
    container.style.display = "none";
  }
}

function changeSelectedSeason() {
  const select = document.getElementById("selected-season");
  if (!select) return;
  activeSeason = select.value;
  visibleMatchesLimit = 50; // reset pagination limit
  renderFilteredMatches();
}

function renderFilteredMatches() {
  const matchesContainer = document.getElementById("matches-list");
  if (!matchesContainer) return;

  // Filter matches based on activeSeason
  let filtered = currentMatchesCache;
  if (activeSeason !== "all") {
    filtered = currentMatchesCache.filter((m) => {
      let sYear = null;
      if (m.payload) {
        try {
          const p =
            typeof m.payload === "string" ? JSON.parse(m.payload) : m.payload;
          sYear = p.season_year || p.season;
        } catch (e) {}
      }
      return String(sYear) === activeSeason;
    });
  }

  // Sort matches by match_date desc
  filtered.sort(
    (a, b) => new Date(b.match_date || 0) - new Date(a.match_date || 0),
  );

  // Update stats summary for the selected season dynamically
  updateStatsSummaryForFiltered(filtered);

  if (filtered.length === 0) {
    matchesContainer.innerHTML = `<div style="color: var(--text-muted); padding: 2rem; text-align: center;">No hay partidos registrados para esta temporada.</div>`;
    return;
  }

  if (activeView === "matches") {
    // Paginate matches rendering
    const paginated = filtered.slice(0, visibleMatchesLimit);
    renderMatchesView(paginated, matchesContainer);

    // Add load-more button if there are remaining matches
    if (filtered.length > visibleMatchesLimit) {
      const loadMoreContainer = document.createElement("div");
      loadMoreContainer.style.cssText = "text-align: center; margin: 1.5rem 0;";

      const loadMoreBtn = document.createElement("button");
      loadMoreBtn.className = "tab-btn";
      loadMoreBtn.style.cssText =
        "background: rgba(99,102,241,0.15); border: 1px solid var(--accent); color: var(--accent-light); padding: 0.5rem 2rem; border-radius: 6px; font-weight: 600; cursor: pointer; transition: all 0.2s;";
      loadMoreBtn.textContent = `⚡ Cargar más partidos (mostrando ${visibleMatchesLimit} de ${filtered.length})`;
      loadMoreBtn.onclick = () => {
        visibleMatchesLimit += 50;
        renderFilteredMatches();
      };

      loadMoreContainer.appendChild(loadMoreBtn);
      matchesContainer.appendChild(loadMoreContainer);
    }
  } else {
    renderMarketsView(filtered, matchesContainer);
  }
}

function renderMatchesView(filtered, matchesContainer) {
  const cards = filtered.map((match) => {
    let scoreText = "-";
    if (match.final_score_home != null && match.final_score_away != null) {
      scoreText = `${match.final_score_home} - ${match.final_score_away}`;
    }

    const statsBadge =
      match.has_real_stats === false
        ? `<span class="badge-stats-missing" style="margin-left: 8px;">Sin stats de temporada</span>`
        : "";

    // Build a success map from compare_response_snapshot if available
    const successMap = {};
    try {
      const snap = match.compare_response_snapshot;
      if (snap && snap.values && Array.isArray(snap.values)) {
        snap.values.forEach((v) => {
          const key = (v.selection || "").toLowerCase();
          if (key) successMap[key] = v.success;
        });
      }
    } catch (_) {}

    const rawPicks = Array.isArray(match.picks_calculados)
      ? match.picks_calculados
      : [];

    const visiblePicks = rawPicks.filter(
      (p) => p.is_publishable || p.is_underdog || p.is_value,
    );

    // Calculate total match profit/units considering all visible picks
    const useStake = localStorage.getItem("use_stake_system") === "true";
    let totalProfit = 0;
    let hasResolvedPicks = false;
    visiblePicks.forEach((pick) => {
      const sel = pick.selection || "";
      const odds =
        typeof pick.odds === "number" ? pick.odds : parseFloat(pick.odds) || 0;
      let success = pick.success;
      if (success === undefined || success === null) {
        success = successMap[sel.toLowerCase()];
      }

      const pickStake = useStake
        ? pick.stake_units !== undefined && pick.stake_units !== null
          ? pick.stake_units
          : pick.kelly_fraction > 0
            ? Math.min(
                MAX_STAKE,
                Math.max(MIN_STAKE, Math.round(pick.kelly_fraction * 100)),
              )
            : MIN_STAKE
        : MIN_STAKE;

      if (success === true) {
        totalProfit += (odds - 1) * pickStake;
        hasResolvedPicks = true;
      } else if (success === false) {
        totalProfit -= pickStake;
        hasResolvedPicks = true;
      } else if (success === "void") {
        hasResolvedPicks = true;
      }
    });

    let matchUnitsText = "";
    if (hasResolvedPicks) {
      const sign = totalProfit >= 0 ? "+" : "";
      const color = totalProfit >= 0 ? "var(--green)" : "var(--red)";
      matchUnitsText = `<span style="color: ${color}; font-weight: bold; margin-left: 6px; font-size: 0.9em;">(${sign}${totalProfit.toFixed(2)}u)</span>`;
    }

    let picksHtml = "";
    if (visiblePicks.length > 0) {
      picksHtml = visiblePicks
        .map((pick) => {
          const sel = pick.selection || "N/A";
          const odds =
            typeof pick.odds === "number"
              ? pick.odds
              : parseFloat(pick.odds) || 0;

          // Use success injected by _populate_history_extra_fields, or look up from snapshot
          let success = pick.success;
          if (success === undefined || success === null) {
            success = successMap[sel.toLowerCase()];
          }

          let badge;
          if (success === true) {
            badge = `<span class="badge-success">✅ Acertado</span>`;
          } else if (success === false) {
            badge = `<span class="badge-fail">❌ Fallo</span>`;
          } else if (success === "void") {
            badge = `<span class="badge-void" style="background-color: rgba(148, 163, 184, 0.2); color: #94a3b8; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; font-weight: 600; border: 1px solid rgba(148, 163, 184, 0.3);">↩️ Nulo</span>`;
          } else {
            badge = `<span class="badge-pending">⏳ Pendiente</span>`;
          }

          // Category badge
          let catBadge = "";
          if (pick.is_underdog) {
            catBadge =
              '<span style="font-size:0.7rem; color:#a78bfa; margin-left:4px;">🐕 Dog</span>';
          } else if (pick.is_publishable || pick.is_value) {
            catBadge =
              '<span style="font-size:0.7rem; color:#60a5fa; margin-left:4px;">🎯 Pro</span>';
          }

          // Recommended stake
          const pickStake = useStake
            ? pick.stake_units !== undefined && pick.stake_units !== null
              ? pick.stake_units
              : pick.kelly_fraction > 0
                ? Math.min(
                    MAX_STAKE,
                    Math.max(MIN_STAKE, Math.round(pick.kelly_fraction * 100)),
                  )
                : MIN_STAKE
            : MIN_STAKE;
          const stakeHtml = useStake
            ? `<span style="font-size:0.75rem; color:var(--accent-light); margin-left:6px; font-weight:bold;">Stake ${pickStake}</span>`
            : "";

          return `
            <div class="pick-row">
              <div style="display:flex; align-items:center; gap:4px; flex-wrap:wrap;">
                <span style="font-weight: 600; color: #fff;">${escapeHtml(sel)}</span>
                ${catBadge}
                <span style="color: var(--text-muted); font-size: 0.8rem;">@${odds.toFixed(2)}</span>
                ${stakeHtml}
              </div>
              <div>${badge}</div>
            </div>
          `;
        })
        .join("");
    } else {
      picksHtml = `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 0.5rem 0;">Sin picks de valor registrados.</div>`;
    }

    const matchDateStr = match.match_date
      ? new Date(match.match_date).toLocaleString("es-ES", {
          dateStyle: "short",
          timeStyle: "short",
        })
      : "Fecha no disponible";

    return `
        <div class="match-card">
          <div class="match-card__header">
            <div>
              <a href="/compare?load_id=${match.id}" style="color: inherit; text-decoration: none;">
                <span class="match-card__title" style="cursor: pointer; transition: color 0.2s;" onmouseover="this.style.color='var(--accent-light)'" onmouseout="this.style.color=''">${escapeHtml(match.match_title)}</span>
              </a>
              ${matchUnitsText}
              ${statsBadge}
            </div>
            <div style="display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;">
              <label style="display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.78rem; color: var(--text-muted); cursor: pointer; user-select: none;">
                <input type="checkbox" ${match.count_in_profitability !== false ? "checked" : ""} onchange="toggleMatchProfitability('${match.id}', this.checked)" style="width: 14px; height: 14px; accent-color: var(--accent); cursor: pointer;">
                Rentabilidad
              </label>
              <span style="font-weight: 800; color: var(--accent-light); font-size: 1.1rem; background: rgba(255,255,255,0.03); padding: 4px 10px; border-radius: 6px;">${scoreText}</span>
              <span class="match-card__date">${matchDateStr}</span>
            </div>
          </div>
          <div class="match-card__body">
            <div style="font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.75rem;">Picks Evaluados</div>
            ${picksHtml}
          </div>
        </div>
      `;
  });

  matchesContainer.innerHTML = cards.join("");
}

function renderMarketsView(filtered, matchesContainer) {
  const useStake = localStorage.getItem("use_stake_system") === "true";
  const marketMap = {};

  filtered.forEach((match) => {
    // Build success map
    const successMap = {};
    try {
      const snap = match.compare_response_snapshot;
      if (snap && snap.values && Array.isArray(snap.values)) {
        snap.values.forEach((v) => {
          const key = (v.selection || "").toLowerCase();
          if (key) successMap[key] = v.success;
        });
      }
    } catch (_) {}

    const rawPicks = Array.isArray(match.picks_calculados)
      ? match.picks_calculados
      : [];

    const visiblePicks = rawPicks.filter(
      (p) => p.is_publishable || p.is_underdog || p.is_value,
    );

    visiblePicks.forEach((pick) => {
      const originalSel = pick.selection || "N/A";
      let selKey = originalSel.trim();
      const lowerSel = selKey.toLowerCase();

      // Determine category for Over/Under markets
      let category = "";
      if (lowerSel.includes("corner") || lowerSel.includes("córner")) {
        category = "Córners";
      } else if (
        lowerSel.includes("tarjeta") ||
        lowerSel.includes("card") ||
        lowerSel.includes("amarilla")
      ) {
        category = "Tarjetas";
      } else if (lowerSel.includes("foul") || lowerSel.includes("falta")) {
        category = "Faltas";
      } else if (
        lowerSel.includes("shot_target") ||
        lowerSel.includes("tiro_a_puerta") ||
        lowerSel.includes("shots_target") ||
        lowerSel.includes("pta")
      ) {
        category = "Tiros a puerta";
      } else if (
        lowerSel.includes("shot") ||
        lowerSel.includes("tiro") ||
        lowerSel.includes("remate")
      ) {
        category = "Tiros";
      } else if (lowerSel.includes("goal") || lowerSel.includes("gol")) {
        category = "Goles";
      }

      if (category) {
        if (
          lowerSel.includes("over") ||
          lowerSel.includes("más de") ||
          lowerSel.includes("mas de")
        ) {
          selKey = `Over ${category}`;
        } else if (
          lowerSel.includes("under") ||
          lowerSel.includes("menos de")
        ) {
          selKey = `Under ${category}`;
        }
      }
      const odds =
        typeof pick.odds === "number" ? pick.odds : parseFloat(pick.odds) || 0;
      let success = pick.success;
      if (success === undefined || success === null) {
        success = successMap[originalSel.toLowerCase()];
      }

      const pickStake = useStake
        ? pick.stake_units !== undefined && pick.stake_units !== null
          ? pick.stake_units
          : pick.kelly_fraction > 0
            ? Math.min(
                MAX_STAKE,
                Math.max(MIN_STAKE, Math.round(pick.kelly_fraction * 100)),
              )
            : MIN_STAKE
        : MIN_STAKE;

      if (!marketMap[selKey]) {
        marketMap[selKey] = {
          name: selKey,
          totalPicks: 0,
          ganados: 0,
          perdidos: 0,
          nulos: 0,
          pendientes: 0,
          profit: 0.0,
          oddsSum: 0.0,
          oddsCount: 0,
        };
      }

      const mData = marketMap[selKey];
      mData.totalPicks += 1;

      if (success === true) {
        mData.ganados += 1;
        mData.profit += (odds - 1) * pickStake;
      } else if (success === false) {
        mData.perdidos += 1;
        mData.profit -= pickStake;
      } else if (success === "void") {
        mData.nulos += 1;
      } else {
        mData.pendientes += 1;
      }

      // Acumular cuota para promedio (solo picks con cuota válida)
      if (odds > 0) {
        mData.oddsSum += odds;
        mData.oddsCount += 1;
      }
    });
  });

  const markets = Object.values(marketMap);
  // Sort markets by totalPicks desc
  markets.sort((a, b) => b.totalPicks - a.totalPicks);

  if (markets.length === 0) {
    matchesContainer.innerHTML = `<div style="color: var(--text-muted); padding: 2rem; text-align: center;">No hay mercados registrados para esta temporada.</div>`;
    return;
  }

  const cardsHtml = markets.map((m) => {
    const resolved = m.ganados + m.perdidos + m.nulos;
    const accuracy =
      m.ganados + m.perdidos > 0
        ? Math.round((m.ganados / (m.ganados + m.perdidos)) * 100)
        : 0;
    const profitSign = m.profit >= 0 ? "+" : "";
    const profitColor = m.profit >= 0 ? "var(--green)" : "var(--red)";
    const avgOdds = m.oddsCount > 0 ? m.oddsSum / m.oddsCount : 0;
    const avgOddsDisplay = avgOdds > 0 ? avgOdds.toFixed(2) : "0.00";
    const winPct = avgOdds > 0 ? ((1 / avgOdds) * 100).toFixed(1) : "0.0";

    return `
      <div class="match-card">
        <div class="match-card__header" style="border-bottom: none; padding-bottom: 0.5rem;">
          <span class="match-card__title" style="font-size: 1.15rem; font-weight: 700; color: #fff;">📊 ${escapeHtml(m.name)}</span>
          <span style="font-weight: 800; color: ${profitColor}; font-size: 1.1rem; background: rgba(255,255,255,0.03); padding: 4px 10px; border-radius: 6px;">
            ${profitSign}${m.profit.toFixed(2)} u
          </span>
        </div>
        <div class="match-card__body" style="padding-top: 0.5rem;">
          <div class="league-stats-grid" style="grid-template-columns: repeat(7, 1fr); gap: 0.75rem;">
            <div class="league-stat-box" style="padding: 0.5rem; background: rgba(255,255,255,0.01);">
              <div class="league-stat-box__val" style="font-size: 1.1rem;">${m.totalPicks}</div>
              <div class="league-stat-box__lbl" style="font-size: 0.65rem;">Picks</div>
            </div>
            <div class="league-stat-box" style="padding: 0.5rem; background: rgba(255,255,255,0.01);">
              <div class="league-stat-box__val" style="font-size: 1.1rem; color: var(--green);">${m.ganados}</div>
              <div class="league-stat-box__lbl" style="font-size: 0.65rem;">Ganados</div>
            </div>
            <div class="league-stat-box" style="padding: 0.5rem; background: rgba(255,255,255,0.01);">
              <div class="league-stat-box__val" style="font-size: 1.1rem; color: var(--red);">${m.perdidos}</div>
              <div class="league-stat-box__lbl" style="font-size: 0.65rem;">Perdidos</div>
            </div>
            <div class="league-stat-box" style="padding: 0.5rem; background: rgba(255,255,255,0.01);">
              <div class="league-stat-box__val" style="font-size: 1.1rem; color: #94a3b8;">${m.nulos}</div>
              <div class="league-stat-box__lbl" style="font-size: 0.65rem;">Nulos</div>
            </div>
            <div class="league-stat-box" style="padding: 0.5rem; background: rgba(255,255,255,0.01);">
              <div class="league-stat-box__val" style="font-size: 1.1rem; color: var(--accent-light);">${accuracy}%</div>
              <div class="league-stat-box__lbl" style="font-size: 0.65rem;">Acierto</div>
            </div>
            <div class="league-stat-box" style="padding: 0.5rem; background: rgba(255,255,255,0.01);">
              <div class="league-stat-box__val" style="font-size: 1.1rem; color: #f59e0b;">${avgOddsDisplay}</div>
              <div class="league-stat-box__lbl" style="font-size: 0.65rem;">Cuota Media</div>
            </div>
            <div class="league-stat-box" style="padding: 0.5rem; background: rgba(255,255,255,0.01);">
              <div class="league-stat-box__val" style="font-size: 1.1rem; color: #a78bfa;">${winPct}%</div>
              <div class="league-stat-box__lbl" style="font-size: 0.65rem;">% Ganar</div>
            </div>
          </div>
          ${
            m.pendientes > 0
              ? `
          <div style="margin-top: 0.75rem; text-align: right; font-size: 0.75rem; color: var(--text-secondary);">
            ⏳ ${m.pendientes} pick(s) pendiente(s)
          </div>`
              : ""
          }
        </div>
      </div>
    `;
  });

  matchesContainer.innerHTML = cardsHtml.join("");
}

function escapeHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Safe version for use inside HTML attribute onclick (single-quoted context)
function escapeAttr(str) {
  if (str == null) return "";
  return String(str).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}

function updateStatsSummaryForFiltered(filteredMatches) {
  let visibleMatches = filteredMatches.length; // all matches in view
  let totalPicks = 0; // resolved non-void picks (same as backend)
  let hits = 0;
  let resolvedPicks = 0;
  let totalProfit = 0;

  const useStake = localStorage.getItem("use_stake_system") === "true";

  filteredMatches.forEach((match) => {
    // successMap from snapshot
    const successMap = {};
    try {
      const snap = match.compare_response_snapshot;
      if (snap && snap.values && Array.isArray(snap.values)) {
        snap.values.forEach((v) => {
          const key = (v.selection || "").toLowerCase();
          if (key) successMap[key] = v.success;
        });
      }
    } catch (_) {}

    const rawPicks = Array.isArray(match.picks_calculados)
      ? match.picks_calculados
      : [];
    const visiblePicks = rawPicks.filter(
      (p) =>
        !p.is_blacklisted && (p.is_publishable || p.is_underdog || p.is_value),
    );

    const hasResult = match.final_score_home != null;

    visiblePicks.forEach((pick) => {
      const sel = pick.selection || "";
      const odds =
        typeof pick.odds === "number" ? pick.odds : parseFloat(pick.odds) || 0;
      let success = pick.success;
      if (success === undefined || success === null) {
        success = successMap[sel.toLowerCase()];
      }

      if (!hasResult) return; // pending match: skip

      const pickStake = useStake
        ? pick.stake_units !== undefined && pick.stake_units !== null
          ? pick.stake_units
          : pick.kelly_fraction > 0
            ? Math.min(
                MAX_STAKE,
                Math.max(MIN_STAKE, Math.round(pick.kelly_fraction * 100)),
              )
            : MIN_STAKE
        : MIN_STAKE;

      if (success === "void") {
        // void: counts for profit (0) but not for accuracy or pick total
        return;
      }

      if (success === true) {
        totalProfit += (odds - 1) * pickStake;
        totalPicks++;
        hits++;
        resolvedPicks++;
      } else if (success === false) {
        totalProfit -= pickStake;
        totalPicks++;
        resolvedPicks++;
      }
    });
  });

  const accuracy =
    resolvedPicks > 0 ? Math.round((hits / resolvedPicks) * 100) : 0;

  document.getElementById("lbl-total-matches").textContent = visibleMatches;
  document.getElementById("lbl-total-picks").textContent = totalPicks;
  document.getElementById("lbl-accuracy").textContent = `${accuracy}%`;

  const profitEl = document.getElementById("lbl-profit");
  profitEl.textContent = `${totalProfit >= 0 ? "+" : ""}${totalProfit.toFixed(2)}u`;
  profitEl.style.color = totalProfit >= 0 ? "var(--green)" : "var(--red)";
}

function toggleLeaguesStake() {
  const checkbox = document.getElementById("leagues-use-stake");
  if (checkbox) {
    localStorage.setItem("use_stake_system", checkbox.checked);
  }
  fetchLeagues();
}

async function toggleMatchProfitability(matchId, countInProfitability) {
  try {
    const res = await fetch(
      `/api/v1/analysis/${matchId}/profitability?count_in_profitability=${countInProfitability}`,
      {
        method: "POST",
      },
    );
    if (!res.ok) throw new Error("Error al actualizar");

    // Update local cache item
    const match = currentMatchesCache.find((m) => m.id === matchId);
    if (match) {
      match.count_in_profitability = countInProfitability;
    }

    // Recalculate stats dynamically for active list and update UI
    renderFilteredMatches();

    // Also, fetch the main leagues again to update the left sidebar profit values!
    const useStake = localStorage.getItem("use_stake_system") === "true";
    const resLeagues = await fetch(
      `/api/v1/stats/leagues?use_stake=${useStake}`,
    );
    if (resLeagues.ok) {
      leaguesData = await resLeagues.json();
      leaguesData.sort((a, b) => b.total_profit - a.total_profit);
      renderLeaguesList();
    }
  } catch (error) {
    console.error("Failed to toggle profitability:", error);
    alert("Error al actualizar la rentabilidad: " + error.message);
  }
}
