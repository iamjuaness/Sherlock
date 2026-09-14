// leagues.js - Control de la sección de ligas en Sherlock
let leaguesData = [];
let activeLeague = null;
let activeView = "matches";
let visibleMatchesLimit = 50;
const MAX_STAKE = 3;
const MIN_STAKE = 1;
let isMarketSelectMode = false;
let selectedMarketsSet = new Set();
let currentMarketsList = [];

function switchView(view) {
  activeView = view;
  const tabMatches = document.getElementById("tab-matches");
  const tabMarkets = document.getElementById("tab-markets");
  const tabParams = document.getElementById("tab-params");
  const matchesList = document.getElementById("matches-list");
  const paramsPanel = document.getElementById("params-panel");
  const bulkActions = document.getElementById("markets-bulk-actions");

  [tabMatches, tabMarkets, tabParams].forEach(
    (t) => t && t.classList.remove("active"),
  );

  if (view === "params") {
    tabParams && tabParams.classList.add("active");
    if (matchesList) matchesList.style.display = "none";
    if (paramsPanel) paramsPanel.style.display = "block";
    if (bulkActions) bulkActions.style.display = "none";
    loadLeagueParams();
    return;
  }

  if (matchesList) matchesList.style.display = "block";
  if (paramsPanel) paramsPanel.style.display = "none";

  if (view === "matches") {
    tabMatches && tabMatches.classList.add("active");
    if (bulkActions) bulkActions.style.display = "none";
    isMarketSelectMode = false;
    selectedMarketsSet.clear();
    updateBulkBlacklistButton();
  } else {
    tabMarkets && tabMarkets.classList.add("active");
    if (bulkActions) bulkActions.style.display = "flex";
    // Si entramos a mercados y la liga activa no tiene los mercados cargados en memory, pedirlos de forma rápida
    if (activeLeague) {
      const leagueInfo = leaguesData.find((l) => l.name === activeLeague);
      if (leagueInfo && !leagueInfo.markets) {
        const useStake = localStorage.getItem("use_stake_system") === "true";
        fetch(
          `/api/v1/leagues/${encodeURIComponent(activeLeague)}/markets?use_stake=${useStake}`,
        )
          .then((r) => r.json())
          .then((m) => {
            leagueInfo.markets = m;
            if (activeView === "markets") renderFilteredMatches();
          })
          .catch(() => {});
      }
    }
  }
  renderFilteredMatches();
}

function getLeagueFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const league = params.get("league");
  return league ? decodeURIComponent(league).trim() : null;
}

function updateLeagueUrl(leagueName, replace = false) {
  if (!leagueName) return;
  const url = new URL(window.location.href);
  url.searchParams.set("league", leagueName);
  if (replace) {
    window.history.replaceState({ league: leagueName }, "", url.toString());
  } else {
    const currentLeague = getLeagueFromUrl();
    if (currentLeague !== leagueName) {
      window.history.pushState({ league: leagueName }, "", url.toString());
    }
  }
}

window.addEventListener("popstate", (e) => {
  const urlLeague = getLeagueFromUrl();
  if (urlLeague && leaguesData.some((l) => l.name === urlLeague)) {
    selectLeague(urlLeague, false);
  } else if (leaguesData.length > 0) {
    selectLeague(leaguesData[0].name, false);
  }
});

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

    // Preserve league selection: check URL first, then activeLeague state, fallback to 1st
    const urlLeague = getLeagueFromUrl();
    let targetLeague = null;
    if (urlLeague && leaguesData.some((l) => l.name === urlLeague)) {
      targetLeague = urlLeague;
    } else if (
      activeLeague &&
      leaguesData.some((l) => l.name === activeLeague)
    ) {
      targetLeague = activeLeague;
    } else if (leaguesData.length > 0) {
      targetLeague = leaguesData[0].name;
    }

    if (targetLeague) {
      selectLeague(targetLeague, true, true); // replace URL if initial load
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

  const searchInput = document.getElementById("league-search-input");
  const query = searchInput ? searchInput.value.trim().toLowerCase() : "";

  const listToRender = query
    ? leaguesData.filter((l) => l.name.toLowerCase().includes(query))
    : leaguesData;

  if (listToRender.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 1rem;">No se encontraron competiciones.</div>`;
    return;
  }

  container.innerHTML = listToRender
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

function filterLeaguesList() {
  renderLeaguesList();
}

let activeSeason = "all";
let currentMatchesCache = [];
let currentLeagueFetchController = null;

function selectLeague(name, updateUrl = true, replaceUrl = false) {
  if (currentLeagueFetchController) {
    currentLeagueFetchController.abort();
  }
  currentLeagueFetchController = new AbortController();

  activeLeague = name;
  activeSeason = "all";
  visibleMatchesLimit = 50;

  if (updateUrl) {
    updateLeagueUrl(name, replaceUrl);
  }

  renderLeaguesList();

  const leagueInfo = leaguesData.find((l) => l.name === name);
  if (!leagueInfo) return;

  // Render stats DIRECTAMENTE desde leaguesData (backend)
  document.getElementById("selected-league-name").textContent = leagueInfo.name;

  const chkProf = document.getElementById("chk-league-profitability");
  if (chkProf) {
    chkProf.checked = leagueInfo.is_profitable !== false;
  }

  fetchMatchesForLeague(name, false, currentLeagueFetchController.signal);
}

async function toggleActiveLeagueProfitability(isProfitable) {
  if (!activeLeague) return;
  try {
    const res = await fetch(
      `/api/v1/leagues/${encodeURIComponent(activeLeague)}/profitability?count_in_profitability=${isProfitable}`,
      { method: "POST" },
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    await fetchLeagues();
  } catch (err) {
    console.error("Error al actualizar rentabilidad de liga:", err);
    alert("Error al actualizar rentabilidad de liga: " + err.message);
  }
}

async function deleteCurrentLeague() {
  if (!activeLeague) return;
  if (
    !confirm(
      `¿Estás seguro de eliminar completamente la competición "${activeLeague}" y todos sus partidos asociados? Esta acción no se puede deshacer.`,
    )
  ) {
    return;
  }
  try {
    const res = await fetch(
      `/api/v1/analysis/competition/${encodeURIComponent(activeLeague)}`,
      { method: "DELETE" },
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    alert(data.message || "Competición eliminada.");
    activeLeague = null;
    await fetchLeagues();
  } catch (err) {
    console.error("Error al eliminar competición:", err);
    alert("Error al eliminar la competición: " + err.message);
  }
}

let currentOffset = 0;
let hasMoreMatches = true;

async function fetchMatchesForLeague(name, isLoadMore = false, signal = null) {
  const matchesContainer = document.getElementById("matches-list");
  if (!matchesContainer) return;

  if (!isLoadMore) {
    currentOffset = 0;
    hasMoreMatches = true;
    currentMatchesCache = [];
    visibleMatchesLimit = 50;
    matchesContainer.innerHTML = `<div class="dashboard-loader"><div class="spinner"></div><span>Cargando partidos...</span></div>`;
  }

  try {
    const useStake = localStorage.getItem("use_stake_system") === "true";
    const fetchOptions = signal ? { signal } : {};
    const res = await fetch(
      `/api/v1/leagues/${encodeURIComponent(name)}/matches?use_stake=${useStake}&limit=50&offset=${currentOffset}`,
      fetchOptions,
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const newMatches = await res.json();

    if (activeLeague !== name) return;

    if (newMatches.length < 50) {
      hasMoreMatches = false;
    }

    currentMatchesCache = currentMatchesCache.concat(newMatches);
    currentOffset += newMatches.length;

    if (isLoadMore) {
      visibleMatchesLimit += newMatches.length;
    }

    // Populate Season selector dropdown
    populateSeasonDropdown();

    renderFilteredMatches();
  } catch (error) {
    if (error.name === "AbortError") {
      return; // Petición cancelada intencionalmente al cambiar de liga
    }
    if (activeLeague !== name) return;
    console.error("Error cargando partidos:", error);
    if (!isLoadMore) {
      matchesContainer.innerHTML = `<div style="color: var(--red); padding: 2rem; text-align: center;">❌ Error al cargar partidos: ${escapeHtml(error.message)}</div>`;
    }
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
    if (hasMoreMatches || filtered.length > visibleMatchesLimit) {
      const loadMoreContainer = document.createElement("div");
      loadMoreContainer.style.cssText = "text-align: center; margin: 1.5rem 0;";

      const loadMoreBtn = document.createElement("button");
      loadMoreBtn.className = "tab-btn";
      loadMoreBtn.style.cssText =
        "background: rgba(99,102,241,0.15); border: 1px solid var(--accent); color: var(--accent-light); padding: 0.5rem 2rem; border-radius: 6px; font-weight: 600; cursor: pointer; transition: all 0.2s;";
      loadMoreBtn.textContent = `⚡ Cargar más partidos (cargados ${filtered.length})`;
      loadMoreBtn.onclick = async () => {
        if (hasMoreMatches) {
          loadMoreBtn.disabled = true;
          loadMoreBtn.textContent = "Cargando más partidos...";
          await fetchMatchesForLeague(activeLeague, true);
        } else {
          visibleMatchesLimit += 50;
          renderFilteredMatches();
        }
      };

      loadMoreContainer.appendChild(loadMoreBtn);
      matchesContainer.appendChild(loadMoreContainer);
    }
  } else {
    renderMarketsView(filtered, matchesContainer);
  }
}

// ── Eliminar un análisis del historial ─────────────────────────
async function deleteHistoryEntry(id, leagueName) {
  if (!confirm("¿Estás seguro de que deseas eliminar este registro?")) return;

  try {
    const response = await fetch(`/api/v1/analysis/${id}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error("No se pudo eliminar el registro de la BD.");
    }

    await fetchMatchesForLeague(leagueName);
  } catch (error) {
    console.error("Error al eliminar:", error);
    alert(error.message);
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

          // Hit rate badge if present
          let hrHtml = "";
          if (
            pick.empirical_hit_rate != null ||
            pick.home_hit_rate != null ||
            pick.away_hit_rate != null
          ) {
            const hrVal =
              pick.empirical_hit_rate != null
                ? pick.empirical_hit_rate
                : pick.home_hit_rate || pick.away_hit_rate;
            hrHtml = `<span style="font-size:0.72rem; background:rgba(56,189,248,0.12); color:#38bdf8; border:1px solid rgba(56,189,248,0.25); padding:1px 5px; border-radius:4px; margin-left:4px;" title="Hit rate histórico del pick">🎯 ${Number(hrVal).toFixed(0)}%</span>`;
          }

          // Bookmaker badge
          const bmVal = pick.bookmaker || (match.payload && (match.payload.bookmaker || (match.payload.odds && match.payload.odds.bookmaker)));
          const bmHtml = bmVal
            ? `<span style="font-size:0.72rem; background:rgba(255,255,255,0.06); color:var(--text-muted); border:1px solid rgba(255,255,255,0.12); padding:1px 5px; border-radius:4px; margin-left:4px;" title="Casa de apuestas">🏠 ${escapeHtml(String(bmVal))}</span>`
            : "";

          return `
            <div class="pick-row">
              <div style="display:flex; align-items:center; gap:4px; flex-wrap:wrap;">
                <span style="font-weight: 600; color: #fff;">${escapeHtml(sel)}</span>
                ${catBadge}
                ${hrHtml}
                <span style="color: var(--text-muted); font-size: 0.8rem;">@${odds.toFixed(2)}</span>
                ${bmHtml}
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

    const leagueName = document.getElementById("selected-league-name").value;

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
              <button class="btn-preset" title="Registrar Resultado" onclick="openResultsModal('${match.id}')">🏆</button>
              <button class="btn-preset" style="color: var(--red);" title="Eliminar" onclick="deleteHistoryEntry('${match.id}', '${match.payload.competition}')">🗑️</button>
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
  let markets = [];

  if (activeSeason === "all" && activeLeague) {
    const leagueInfo = leaguesData.find((l) => l.name === activeLeague);
    if (
      leagueInfo &&
      Array.isArray(leagueInfo.markets) &&
      leagueInfo.markets.length > 0
    ) {
      markets = leagueInfo.markets;
    }
  }

  if (!markets || markets.length === 0) {
    const marketMap = {};

    filtered.forEach((match) => {
      // Si el partido está excluido de rentabilidad, no incluir sus picks en la data de mercado (al igual que la cabecera)
      if (match.count_in_profitability === false) return;

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
        (p) =>
          !p.is_blacklisted &&
          !p.is_rule_blocked &&
          (p.is_publishable || p.is_underdog || p.is_value),
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
          typeof pick.odds === "number"
            ? pick.odds
            : parseFloat(pick.odds) || 0;
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

    markets = Object.values(marketMap);
    markets.sort((a, b) => b.totalPicks - a.totalPicks);
  }

  currentMarketsList = markets;

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

    const isChecked = selectedMarketsSet.has(m.name);
    const selectCheckboxHtml = isMarketSelectMode
      ? `<input type="checkbox" ${isChecked ? "checked" : ""} onchange="toggleMarketSelection('${escapeAttr(m.name)}', this.checked)" style="width: 18px; height: 18px; accent-color: var(--accent); cursor: pointer; margin-right: 0.5rem;">`
      : "";

    return `
      <div class="match-card">
        <div class="match-card__header" style="border-bottom: none; padding-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            ${selectCheckboxHtml}
            <span class="match-card__title" style="font-size: 1.15rem; font-weight: 700; color: #fff;">📊 ${escapeHtml(m.name)}</span>
            <button onclick="reduceMarketStake('${escapeAttr(m.name)}')" style="background: rgba(245, 158, 11, 0.12); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.25); padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.72rem; cursor: pointer; transition: 0.2s;" onmouseover="this.style.background='rgba(245, 158, 11, 0.25)'" onmouseout="this.style.background='rgba(245, 158, 11, 0.12)'" title="Reducir stake a la mitad (50%) para este mercado en ${escapeAttr(activeLeague || "")}">📉 Reducir Stake (50%)</button>
            <button onclick="addMarketToBlacklist('${escapeAttr(m.name)}')" style="background: rgba(239, 68, 68, 0.12); color: var(--red); border: 1px solid rgba(239, 68, 68, 0.25); padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.72rem; cursor: pointer; transition: 0.2s;" onmouseover="this.style.background='rgba(239, 68, 68, 0.25)'" onmouseout="this.style.background='rgba(239, 68, 68, 0.12)'" title="Agregar este mercado a la blacklist de ${escapeAttr(activeLeague || "")}">🚫 Blacklist</button>
          </div>
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
              <div class="league-stat-box__val" style="font-size: 1.1rem; color: #38bdf8;">${winPct}%</div>
              <div class="league-stat-box__lbl" style="font-size: 0.65rem;">% Equilibrio</div>
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

async function updateStatsSummaryForFiltered(filteredMatches) {
  //rows = db.query(AnalysisHistory).options(load_only(AnalysisHistory.id)).all();

  matches_count = await fetch(
    `/api/v1/competitions/${activeLeague}/matches`,
  ).then((res) => res.json());

  if (matches_count > 0) {
    document.getElementById("lbl-total-matches").textContent = matches_count;
  }
  // If activeSeason is 'all', keep the official backend aggregated stats for the league
  if (activeSeason === "all" && activeLeague) {
    const leagueInfo = leaguesData.find((l) => l.name === activeLeague);
    if (leagueInfo) {
      document.getElementById("lbl-total-picks").textContent =
        leagueInfo.total_picks;
      document.getElementById("lbl-accuracy").textContent =
        `${leagueInfo.accuracy}%`;
      const profitEl = document.getElementById("lbl-profit");
      profitEl.textContent = `${leagueInfo.total_profit >= 0 ? "+" : ""}${leagueInfo.total_profit.toFixed(2)}u`;
      profitEl.style.color =
        leagueInfo.total_profit >= 0 ? "var(--green)" : "var(--red)";

      const avgOddsEl = document.getElementById("lbl-avg-odds");
      if (avgOddsEl) {
        avgOddsEl.textContent = leagueInfo.avg_odds ? leagueInfo.avg_odds.toFixed(2) : "0.00";
      }
      const breakEvenEl = document.getElementById("lbl-break-even");
      if (breakEvenEl) {
        breakEvenEl.textContent = leagueInfo.break_even_pct ? `${leagueInfo.break_even_pct.toFixed(1)}%` : "0.0%";
      }
      return;
    }
  }

  let visibleMatches = filteredMatches.length; // all matches in view
  let totalPicks = 0; // resolved non-void picks (same as backend)
  let hits = 0;
  let resolvedPicks = 0;
  let totalProfit = 0;
  let oddsSum = 0;
  let oddsCount = 0;

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
        !p.is_blacklisted &&
        !p.is_rule_blocked &&
        (p.is_publishable || p.is_underdog || p.is_value),
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

      if (odds > 0) {
        oddsSum += odds;
        oddsCount += 1;
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
  const avgOdds = oddsCount > 0 ? oddsSum / oddsCount : 0;
  const breakEvenPct = avgOdds > 0 ? (1 / avgOdds) * 100 : 0;

  document.getElementById("lbl-total-matches").textContent = visibleMatches;
  document.getElementById("lbl-total-picks").textContent = totalPicks;
  document.getElementById("lbl-accuracy").textContent = `${accuracy}%`;

  const profitEl = document.getElementById("lbl-profit");
  profitEl.textContent = `${totalProfit >= 0 ? "+" : ""}${totalProfit.toFixed(2)}u`;
  profitEl.style.color = totalProfit >= 0 ? "var(--green)" : "var(--red)";

  const avgOddsEl = document.getElementById("lbl-avg-odds");
  if (avgOddsEl) {
    avgOddsEl.textContent = avgOdds > 0 ? avgOdds.toFixed(2) : "0.00";
  }
  const breakEvenEl = document.getElementById("lbl-break-even");
  if (breakEvenEl) {
    breakEvenEl.textContent = breakEvenPct > 0 ? `${breakEvenPct.toFixed(1)}%` : "0.0%";
  }
}

function toggleMarketSelectMode() {
  isMarketSelectMode = !isMarketSelectMode;
  const selectBtn = document.getElementById("btn-select-markets");
  const selectAllBtn = document.getElementById("btn-select-all-markets");
  const applyBtn = document.getElementById("btn-apply-bulk-blacklist");

  if (isMarketSelectMode) {
    if (selectBtn) {
      selectBtn.innerHTML = "❌ Cancelar Selección";
      selectBtn.style.background = "rgba(239, 68, 68, 0.15)";
      selectBtn.style.borderColor = "var(--red)";
      selectBtn.style.color = "var(--red)";
    }
    if (selectAllBtn) selectAllBtn.style.display = "inline-flex";
    if (applyBtn) applyBtn.style.display = "inline-flex";
  } else {
    selectedMarketsSet.clear();
    if (selectBtn) {
      selectBtn.innerHTML = "☑️ Seleccionar";
      selectBtn.style.background = "rgba(99, 102, 241, 0.15)";
      selectBtn.style.borderColor = "var(--accent)";
      selectBtn.style.color = "var(--accent-light)";
    }
    if (selectAllBtn) selectAllBtn.style.display = "none";
    if (applyBtn) applyBtn.style.display = "none";
  }
  updateBulkBlacklistButton();
  renderFilteredMatches();
}

function toggleMarketSelection(marketName, isChecked) {
  if (isChecked) {
    selectedMarketsSet.add(marketName);
  } else {
    selectedMarketsSet.delete(marketName);
  }
  updateBulkBlacklistButton();
  renderFilteredMatches();
}

function toggleSelectAllMarkets() {
  if (!currentMarketsList || currentMarketsList.length === 0) return;
  const allSelected = currentMarketsList.every((m) => selectedMarketsSet.has(m.name));
  if (allSelected) {
    selectedMarketsSet.clear();
  } else {
    currentMarketsList.forEach((m) => selectedMarketsSet.add(m.name));
  }
  updateBulkBlacklistButton();
  renderFilteredMatches();
}

function updateBulkBlacklistButton() {
  const applyBtn = document.getElementById("btn-apply-bulk-blacklist");
  const selectAllBtn = document.getElementById("btn-select-all-markets");
  if (!applyBtn) return;

  const count = selectedMarketsSet.size;
  applyBtn.textContent = `🚫 Aplicar Blacklist (${count})`;

  if (count > 0) {
    applyBtn.disabled = false;
    applyBtn.style.opacity = "1";
    applyBtn.style.cursor = "pointer";
  } else {
    applyBtn.disabled = true;
    applyBtn.style.opacity = "0.6";
    applyBtn.style.cursor = "not-allowed";
  }

  if (selectAllBtn && currentMarketsList.length > 0) {
    const allSelected = currentMarketsList.every((m) => selectedMarketsSet.has(m.name));
    selectAllBtn.textContent = allSelected ? "Deseleccionar Todos" : "Seleccionar Todos";
  }
}

async function applyBulkBlacklist() {
  if (!activeLeague || selectedMarketsSet.size === 0) return;
  const count = selectedMarketsSet.size;
  if (
    !confirm(
      `¿Deseas agregar los ${count} mercados seleccionados a la blacklist de la competición "${activeLeague}" y recalcular todo el historial?`
    )
  ) {
    return;
  }

  try {
    const res = await fetch("/api/v1/leagues/blacklist-markets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        league: activeLeague,
        markets: Array.from(selectedMarketsSet),
      }),
    });
    const data = await res.json();
    alert(data.message || "Mercados añadidos a blacklist.");

    isMarketSelectMode = false;
    selectedMarketsSet.clear();
    const selectBtn = document.getElementById("btn-select-markets");
    if (selectBtn) {
      selectBtn.innerHTML = "☑️ Seleccionar";
      selectBtn.style.background = "rgba(99, 102, 241, 0.15)";
      selectBtn.style.borderColor = "var(--accent)";
      selectBtn.style.color = "var(--accent-light)";
    }
    const selectAllBtn = document.getElementById("btn-select-all-markets");
    if (selectAllBtn) selectAllBtn.style.display = "none";
    const applyBtn = document.getElementById("btn-apply-bulk-blacklist");
    if (applyBtn) applyBtn.style.display = "none";

    await fetchLeagues();
  } catch (err) {
    console.error("Error al agregar mercados a blacklist:", err);
    alert("Error al aplicar la blacklist: " + err.message);
  }
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

async function addMarketToBlacklist(marketName) {
  if (!activeLeague) return;
  if (
    !confirm(
      `¿Deseas agregar el mercado "${marketName}" a la blacklist de la competición "${activeLeague}" y aplicar a todos los picks del historial?`,
    )
  ) {
    return;
  }
  try {
    const res = await fetch("/api/v1/leagues/blacklist-market", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        league: activeLeague,
        market_name: marketName,
      }),
    });
    const data = await res.json();
    alert(data.message || "Mercado añadido a blacklist.");

    // Recargar ligas para refrescar rentabilidades manteniendo la liga activa seleccionada
    await fetchLeagues();
  } catch (err) {
    console.error("Error al agregar mercado a blacklist:", err);
    alert("Error al agregar a blacklist: " + err.message);
  }
}

async function reduceMarketStake(marketName) {
  if (!activeLeague) return;
  if (
    !confirm(
      `¿Deseas reducir el stake a la mitad (50%) para el mercado "${marketName}" en la competición "${activeLeague}" y recalcular todo el historial?`,
    )
  ) {
    return;
  }
  try {
    const res = await fetch("/api/v1/leagues/reduce-stake-market", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        league: activeLeague,
        market_name: marketName,
        stake_modifier: 0.5,
      }),
    });
    const data = await res.json();
    alert(data.message || "Stake reducido con éxito.");

    // Recargar ligas para refrescar estadísticas manteniendo la liga activa seleccionada
    await fetchLeagues();
  } catch (err) {
    console.error("Error al reducir stake del mercado:", err);
    alert("Error al reducir stake: " + err.message);
  }
}
