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

function isZeroH2hPick(p) {
  if (!p) return false;
  const h2hCount =
    p.h2h_samples != null
      ? p.h2h_samples
      : Array.isArray(p.h2h_matches)
        ? p.h2h_matches.length
        : 0;
  if (h2hCount <= 0) return false;

  const h2hHits =
    p.h2h_hits != null
      ? p.h2h_hits
      : Array.isArray(p.h2h_matches)
        ? p.h2h_matches.filter((m) => m.hit === true).length
        : null;
  if (h2hHits === 0) return true;

  const h2hHr =
    p.h2h_hit_rate != null
      ? Number(p.h2h_hit_rate)
      : p.h2h_raw_hit_rate != null
        ? Number(p.h2h_raw_hit_rate)
        : null;
  if (h2hHr === 0) return true;

  return false;
}

function getCanonicalMarketKey(pick, snapObj = {}) {
  const originalSel = (pick.selection || "N/A").trim();
  const lowerSel = originalSel.toLowerCase();
  const effectiveLine =
    pick.line !== undefined && pick.line !== null ? pick.line : snapObj.line;

  let familyLabel = "";
  let hasLine = true;

  if (
    lowerSel === "empate" ||
    lowerSel === "draw" ||
    /\b(empate|draw)\b/i.test(lowerSel)
  ) {
    familyLabel = "Empate";
    hasLine = false;
  } else if (
    lowerSel === "local" ||
    lowerSel === "home" ||
    lowerSel === "victoria local" ||
    /\b(local|victoria local)\b/i.test(lowerSel)
  ) {
    familyLabel = "Local";
    hasLine = false;
  } else if (
    lowerSel === "visitante" ||
    lowerSel === "away" ||
    lowerSel === "victoria visitante" ||
    /\b(visitante|victoria visitante)\b/i.test(lowerSel)
  ) {
    familyLabel = "Visitante";
    hasLine = false;
  } else {
    const isShotsTargetText =
      lowerSel.includes("shot_target") ||
      lowerSel.includes("shots_target") ||
      lowerSel.includes("tiro_a_puerta") ||
      lowerSel.includes("tiros_a_puerta") ||
      lowerSel.includes("remates a puerta") ||
      lowerSel.includes("tiros a puerta") ||
      lowerSel.includes("shots on target") ||
      lowerSel.includes("tiros al arco") ||
      lowerSel.includes("remates al arco") ||
      lowerSel.includes("tiro al arco") ||
      lowerSel.includes("tiro a puerta") ||
      lowerSel.includes("tiros a pta") ||
      lowerSel.includes("tiro a pta") ||
      lowerSel.includes("a pta") ||
      /\b(sot)\b/i.test(lowerSel);

    if (isShotsTargetText) {
      familyLabel = "Tiros a puerta";
    } else {
      const mFam = (
        pick.market_family ||
        snapObj.market_family ||
        ""
      ).toLowerCase();
      if (
        mFam === "shots_target" ||
        mFam === "shots_on_target" ||
        mFam === "tiros_a_puerta" ||
        mFam === "shot_on_target"
      ) {
        familyLabel = "Tiros a puerta";
      } else if (mFam === "shots" || mFam === "tiros") {
        familyLabel = "Tiros";
      } else if (mFam === "btts") {
        familyLabel = "BTTS";
        hasLine = false;
      } else if (mFam === "double_chance" || mFam === "doublechance") {
        familyLabel = "Doble Oportunidad";
        hasLine = false;
      } else if (mFam === "cards" || mFam === "tarjetas") {
        familyLabel = "Tarjetas";
      } else if (mFam === "corners" || mFam === "córners") {
        familyLabel = "Córners";
      } else if (mFam === "goals" || mFam === "goles") {
        familyLabel = "Goles";
      } else if (mFam === "fouls" || mFam === "faltas") {
        familyLabel = "Faltas";
      }
    }

    if (!familyLabel) {
      if (
        lowerSel.includes("btts") ||
        lowerSel.includes("ambos marcan") ||
        lowerSel.includes("both teams to score")
      ) {
        familyLabel = "BTTS";
        hasLine = false;
      } else if (
        lowerSel.includes("doble oportunidad") ||
        lowerSel.includes("double chance")
      ) {
        familyLabel = "Doble Oportunidad";
        hasLine = false;
      } else if (
        lowerSel.includes("tarjeta") ||
        lowerSel.includes("card") ||
        lowerSel.includes("amarilla")
      ) {
        familyLabel = "Tarjetas";
      } else if (
        lowerSel.includes("corner") ||
        lowerSel.includes("córner") ||
        lowerSel.includes("saques de esquina")
      ) {
        familyLabel = "Córners";
      } else if (isShotsTargetText) {
        familyLabel = "Tiros a puerta";
      } else if (
        lowerSel.includes("shot") ||
        lowerSel.includes("tiro") ||
        lowerSel.includes("remate")
      ) {
        familyLabel = "Tiros";
      } else if (lowerSel.includes("foul") || lowerSel.includes("falta")) {
        familyLabel = "Faltas";
      } else if (
        lowerSel.includes("gol") ||
        lowerSel.includes("goal") ||
        lowerSel.includes("over") ||
        lowerSel.includes("under")
      ) {
        familyLabel = "Goles";
      }
    }
  }

  let sideLabel = "";
  if (familyLabel === "BTTS") {
    if (
      lowerSel.includes("yes") ||
      lowerSel.includes("sí") ||
      lowerSel === "si" ||
      lowerSel.endsWith(" si")
    ) {
      sideLabel = "Sí";
    } else if (lowerSel.includes("no")) {
      sideLabel = "No";
    }
  } else if (familyLabel === "Doble Oportunidad") {
    if (
      lowerSel.includes("homedraw") ||
      lowerSel.includes("home draw") ||
      /\b1x\b/i.test(lowerSel)
    ) {
      sideLabel = "1X";
    } else if (
      lowerSel.includes("homeaway") ||
      lowerSel.includes("home away") ||
      /\b12\b/i.test(lowerSel)
    ) {
      sideLabel = "12";
    } else if (
      lowerSel.includes("drawaway") ||
      lowerSel.includes("draw away") ||
      /\bx2\b/i.test(lowerSel)
    ) {
      sideLabel = "X2";
    }
  } else if (
    familyLabel === "Local" ||
    familyLabel === "Empate" ||
    familyLabel === "Visitante"
  ) {
    sideLabel = "";
  } else {
    if (
      lowerSel.includes("over") ||
      lowerSel.includes("más de") ||
      lowerSel.includes("mas de")
    ) {
      sideLabel = "Over";
    } else if (
      lowerSel.includes("under") ||
      lowerSel.includes("menos de")
    ) {
      sideLabel = "Under";
    }
  }

  let lineVal = null;
  if (hasLine) {
    lineVal =
      effectiveLine !== undefined && effectiveLine !== null
        ? effectiveLine
        : null;
    if (lineVal === null) {
      const numMatch = originalSel.match(/(\d+(?:\.\d+)?)/);
      if (numMatch) lineVal = parseFloat(numMatch[1]);
    }
  }

  const lineStr = hasLine && lineVal !== null ? ` ${lineVal}` : "";

  if (
    familyLabel === "Local" ||
    familyLabel === "Empate" ||
    familyLabel === "Visitante"
  ) {
    return familyLabel;
  } else if (
    familyLabel === "Doble Oportunidad" ||
    familyLabel === "BTTS"
  ) {
    return sideLabel ? `${familyLabel} ${sideLabel}` : familyLabel;
  } else if (familyLabel) {
    return sideLabel
      ? `${sideLabel}${lineStr} ${familyLabel}`
      : `${familyLabel}${lineStr}`;
  }
  return originalSel;
}

function buildLeagueMarketMap(matches) {
  const map = {};
  const useStake = localStorage.getItem("use_stake_system") !== "false";

  (matches || []).forEach((match) => {
    if (match.count_in_profitability === false) return;

    const snapMap = {};
    try {
      const snap = match.compare_response_snapshot;
      if (snap && snap.values && Array.isArray(snap.values)) {
        snap.values.forEach((v) => {
          const key = (v.selection || "").toLowerCase();
          if (key) snapMap[key] = v;
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
        !isZeroH2hPick(p) &&
        (p.is_publishable || p.is_underdog || p.is_value),
    );

    visiblePicks.forEach((pick) => {
      const originalSel = pick.selection || "N/A";
      const snapObj = snapMap[originalSel.toLowerCase()] || {};
      const selKey = getCanonicalMarketKey(pick, snapObj);

      const odds =
        typeof pick.odds === "number" ? pick.odds : parseFloat(pick.odds || 0);
      let success = pick.success;
      if (success === undefined || success === null) {
        success = snapObj.success;
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

      if (!map[selKey]) {
        map[selKey] = {
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

      const mData = map[selKey];
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

      if (odds > 0) {
        mData.oddsSum += odds;
        mData.oddsCount += 1;
      }
    });
  });

  return map;
}

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
    updateBulkGovernanceButtons();
  } else if (view === "markets") {
    tabMarkets && tabMarkets.classList.add("active");
    if (bulkActions) bulkActions.style.display = "flex";
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
      const roiVal =
        league.roi !== undefined
          ? league.roi
          : league.total_picks > 0
            ? (league.total_profit / league.total_picks) * 100
            : 0;
      const roiSign = roiVal >= 0 ? "+" : "";
      return `
      <div class="league-list-item ${activeClass} ${pendingClass}" onclick="selectLeague('${escapeAttr(league.name)}')">
        <span class="league-list-item__name" title="${escapeHtml(league.name)}">🏆 ${escapeHtml(league.name)}</span>
        <span class="league-list-item__profit ${profitClass}">
          ${profitSign}${league.total_profit.toFixed(2)}u
          <span style="font-size: 0.78em; opacity: 0.85; font-weight: 500; margin-left: 2px;">(${roiSign}${roiVal.toFixed(1)}%)</span>
        </span>
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

  // Populate season dropdown from backend data (all matches, not just loaded ones)
  populateSeasonDropdown(leagueInfo.seasons || []);

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
    const seasonParam =
      activeSeason && activeSeason !== "all"
        ? `&season=${encodeURIComponent(activeSeason)}`
        : "";
    const res = await fetch(
      `/api/v1/leagues/${encodeURIComponent(name)}/matches?use_stake=${useStake}&limit=50&offset=${currentOffset}${seasonParam}`,
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

function populateSeasonDropdown(seasons) {
  const select = document.getElementById("selected-season");
  const container = document.getElementById("season-filter-card");
  if (!select || !container) return;

  // seasons comes from backend: already sorted descending (all matches, not just loaded)
  if (!seasons || seasons.length === 0) {
    container.style.display = "none";
    return;
  }

  container.style.display = "flex";

  let html = '<option value="all">Todas las temporadas</option>';
  seasons.forEach((s) => {
    html += `<option value="${escapeHtml(String(s))}">${escapeHtml(String(s))}</option>`;
  });
  select.innerHTML = html;
  select.value = activeSeason;
}

function changeSelectedSeason() {
  const select = document.getElementById("selected-season");
  if (!select) return;

  if (currentLeagueFetchController) {
    currentLeagueFetchController.abort();
  }
  currentLeagueFetchController = new AbortController();

  activeSeason = select.value;
  visibleMatchesLimit = 50;
  currentOffset = 0;
  hasMoreMatches = true;
  currentMatchesCache = [];

  const matchesContainer = document.getElementById("matches-list");
  if (matchesContainer) {
    matchesContainer.innerHTML = `<div class="dashboard-loader"><div class="spinner"></div><span>Cargando partidos...</span></div>`;
  }

  fetchMatchesForLeague(
    activeLeague,
    false,
    currentLeagueFetchController.signal,
  );
}

function renderFilteredMatches() {
  const matchesContainer = document.getElementById("matches-list");
  if (!matchesContainer) return;

  // El filtro de temporada lo aplica el backend al fetchear.
  // currentMatchesCache ya contiene solo los partidos de la temporada activa.
  let filtered = currentMatchesCache;

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
  } else if (activeView === "markets") {
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

function getLeagueMarketStats(pick, snapObj, activeLeagueName, currentMatches) {
  const selKey = getCanonicalMarketKey(pick, snapObj);
  const kLower = selKey.trim().toLowerCase();

  let mStats = null;
  if (activeLeagueName) {
    const leagueInfo = leaguesData.find((l) => l.name === activeLeagueName);
    if (
      leagueInfo &&
      Array.isArray(leagueInfo.markets) &&
      leagueInfo.markets.length > 0
    ) {
      mStats = leagueInfo.markets.find(
        (m) => m && m.name && m.name.trim().toLowerCase() === kLower,
      );
    }
  }

  if (!mStats) {
    const localMap = buildLeagueMarketMap(currentMatches || []);
    mStats = localMap[selKey] || localMap[kLower];
  }

  return { selKey, mStats };
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
    const snapMap = {};
    try {
      const snap = match.compare_response_snapshot;
      if (snap && snap.values && Array.isArray(snap.values)) {
        snap.values.forEach((v) => {
          const key = (v.selection || "").toLowerCase();
          if (key) {
            successMap[key] = v.success;
            snapMap[key] = v;
          }
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
        !isZeroH2hPick(p) &&
        (p.is_publishable || p.is_underdog || p.is_value),
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
          const bmVal =
            pick.bookmaker ||
            (match.payload &&
              (match.payload.bookmaker ||
                (match.payload.odds && match.payload.odds.bookmaker)));
          const bmHtml = bmVal
            ? `<span style="font-size:0.72rem; background:rgba(255,255,255,0.06); color:var(--text-muted); border:1px solid rgba(255,255,255,0.12); padding:1px 5px; border-radius:4px; margin-left:4px;" title="Casa de apuestas">🏠 ${escapeHtml(String(bmVal))}</span>`
            : "";

          // Market performance tooltip badge (i)
          const snapObj = snapMap[sel.toLowerCase()] || {};
          const compName = activeLeague || match.competition || "esta liga";
          const { selKey, mStats } = getLeagueMarketStats(
            pick,
            snapObj,
            compName,
            currentMatchesCache,
          );

          let mTooltip = "";
          const resolved = mStats ? (mStats.ganados + mStats.perdidos + mStats.nulos) : 0;

          if (!mStats || mStats.totalPicks <= 0) {
            mTooltip = `Competición: ${compName}\nMercado: ${selKey}\n---------------------------------\n🥇 Primer pick registrado para este mercado en esta liga (sin historial previo)`;
          } else if (resolved === 0) {
            const pendStr = mStats.pendientes > 0 ? ` (${mStats.pendientes} pendiente${mStats.pendientes > 1 ? "s" : ""})` : "";
            mTooltip = `Rendimiento del mercado en ${compName}\nMercado: ${selKey}\n---------------------------------\n⏳ Sin picks evaluados aún${pendStr}\n(El historial se calculará una vez finalice algún partido)`;
          } else {
            const accuracyPct =
              (mStats.ganados + mStats.perdidos) > 0
                ? `${Math.round((mStats.ganados / (mStats.ganados + mStats.perdidos)) * 100)}% (${mStats.ganados}/${mStats.ganados + mStats.perdidos})`
                : "N/A";
            const sign = mStats.profit >= 0 ? "+" : "";
            const avgOdds =
              mStats.oddsCount > 0
                ? (mStats.oddsSum / mStats.oddsCount).toFixed(2)
                : "-";
            const pendStr =
              mStats.pendientes > 0 ? ` (+ ${mStats.pendientes} pend)` : "";

            mTooltip = `Rendimiento del mercado en ${compName}\nMercado: ${selKey}\n---------------------------------\n📊 Picks evaluados: ${resolved}${pendStr}\n🏆 Historial: ${mStats.ganados}W - ${mStats.perdidos}L - ${mStats.nulos}V\n🎯 Acierto: ${accuracyPct}\n💰 Profit: ${sign}${mStats.profit.toFixed(2)}u\n🎲 Cuota Media: @${avgOdds}`;
          }

          const infoIconHtml = `<span style="font-size:0.72rem; background:rgba(56,189,248,0.08); color:#38bdf8; border:1px solid rgba(56,189,248,0.25); padding:1px 5px; border-radius:10px; margin-left:4px; cursor:help; font-weight:600; display:inline-flex; align-items:center;" title="${escapeHtml(mTooltip)}">ℹ️</span>`;

          return `
            <div class="pick-row">
              <div style="display:flex; align-items:center; gap:4px; flex-wrap:wrap;">
                <span style="font-weight: 600; color: #fff;">${escapeHtml(sel)}</span>
                ${catBadge}
                ${hrHtml}
                <span style="color: var(--text-muted); font-size: 0.8rem;">@${odds.toFixed(2)}</span>
                ${bmHtml}
                ${stakeHtml}
                ${infoIconHtml}
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
  const useStake = localStorage.getItem("use_stake_system") !== "false";

  let markets;
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
    const marketMap = buildLeagueMarketMap(filtered);
    markets = Object.values(marketMap);
    markets.sort((a, b) => b.totalPicks - a.totalPicks);
  }

  currentMarketsList = markets;

  if (markets.length === 0) {
    matchesContainer.innerHTML =
      '<div style="color: var(--text-muted); padding: 2rem; text-align: center;">No hay mercados registrados para esta temporada.</div>';
    return;
  }

  const cardsHtml = markets.map((m) => {
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
      ? `<input type="checkbox" ${
          isChecked ? "checked" : ""
        } onchange="toggleMarketSelection('${escapeAttr(
          m.name,
        )}', this.checked)" style="width: 18px; height: 18px; accent-color: var(--accent); cursor: pointer; margin-right: 0.5rem;">`
      : "";

    return `
      <div class="match-card">
        <div class="match-card__header" style="border-bottom: none; padding-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            ${selectCheckboxHtml}
            <span class="match-card__title" style="font-size: 1.15rem; font-weight: 700; color: #fff;">📊 ${escapeHtml(m.name)}</span>
            <button onclick="reduceMarketStake('${escapeAttr(m.name)}')" style="background: rgba(245, 158, 11, 0.12); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.25); padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.72rem; cursor: pointer; transition: 0.2s;" onmouseover="this.style.background='rgba(245, 158, 11, 0.25)'" onmouseout="this.style.background='rgba(245, 158, 11, 0.12)'" title="Reducir stake en Segment Governance para ${escapeAttr(activeLeague || "")}">📉 Reducir Stake</button>
            <button onclick="addMarketToBlacklist('${escapeAttr(m.name)}')" style="background: rgba(239, 68, 68, 0.12); color: var(--red); border: 1px solid rgba(239, 68, 68, 0.25); padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.72rem; cursor: pointer; transition: 0.2s;" onmouseover="this.style.background='rgba(239, 68, 68, 0.25)'" onmouseout="this.style.background='rgba(239, 68, 68, 0.12)'" title="Agregar mercado a la blacklist de ${escapeAttr(activeLeague || "")}">🚫 Blacklist</button>
          </div>
          <span style="font-weight: 800; color: ${profitColor}; font-size: 1.1rem; background: rgba(255,255,255,0.03); padding: 4px 10px; border-radius: 6px;">
            ${profitSign}${m.profit.toFixed(2)} u
          </span>
        </div>
        <div class="match-card__body" style="padding-top: 0.5rem;">
          <div class="league-stats-grid" style="grid-template-columns: repeat(8, 1fr); gap: 0.5rem;">
            <div class="league-stat-box" style="padding: 0.5rem; background: rgba(255,255,255,0.01);">
              <div class="league-stat-box__val" style="font-size: 1.1rem;">${m.totalPicks}</div>
              <div class="league-stat-box__lbl" style="font-size: 0.65rem;">Total Picks</div>
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
              <div class="league-stat-box__val" style="font-size: 1.1rem; color: #f59e0b;">${m.pendientes || 0}</div>
              <div class="league-stat-box__lbl" style="font-size: 0.65rem;">Pendientes</div>
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
          <div style="margin-top: 0.75rem; text-align: right; font-size: 0.75rem; color: #f59e0b;">
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
      if (profitEl) {
        profitEl.textContent = `${leagueInfo.total_profit >= 0 ? "+" : ""}${leagueInfo.total_profit.toFixed(2)}u`;
        profitEl.style.color =
          leagueInfo.total_profit >= 0 ? "var(--green)" : "var(--red)";
      }
      const roiEl = document.getElementById("lbl-roi");
      if (roiEl) {
        const roiVal =
          leagueInfo.roi !== undefined
            ? leagueInfo.roi
            : leagueInfo.total_picks > 0
              ? (leagueInfo.total_profit / leagueInfo.total_picks) * 100
              : 0;
        roiEl.textContent = `(${roiVal >= 0 ? "+" : ""}${roiVal.toFixed(1)}%)`;
        roiEl.style.color = roiVal >= 0 ? "var(--green)" : "var(--red)";
      }

      const avgOddsEl = document.getElementById("lbl-avg-odds");
      if (avgOddsEl) {
        avgOddsEl.textContent = leagueInfo.avg_odds
          ? leagueInfo.avg_odds.toFixed(2)
          : "0.00";
      }
      const breakEvenEl = document.getElementById("lbl-break-even");
      if (breakEvenEl) {
        breakEvenEl.textContent = leagueInfo.break_even_pct
          ? `${leagueInfo.break_even_pct.toFixed(1)}%`
          : "0.0%";
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
        !isZeroH2hPick(p) &&
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
  if (profitEl) {
    profitEl.textContent = `${totalProfit >= 0 ? "+" : ""}${totalProfit.toFixed(2)}u`;
    profitEl.style.color = totalProfit >= 0 ? "var(--green)" : "var(--red)";
  }
  const roiEl = document.getElementById("lbl-roi");
  if (roiEl) {
    const roiVal = totalPicks > 0 ? (totalProfit / totalPicks) * 100 : 0;
    roiEl.textContent = `(${roiVal >= 0 ? "+" : ""}${roiVal.toFixed(1)}%)`;
    roiEl.style.color = roiVal >= 0 ? "var(--green)" : "var(--red)";
  }

  const avgOddsEl = document.getElementById("lbl-avg-odds");
  if (avgOddsEl) {
    avgOddsEl.textContent = avgOdds > 0 ? avgOdds.toFixed(2) : "0.00";
  }
  const breakEvenEl = document.getElementById("lbl-break-even");
  if (breakEvenEl) {
    breakEvenEl.textContent =
      breakEvenPct > 0 ? `${breakEvenPct.toFixed(1)}%` : "0.0%";
  }
}

function toggleMarketSelectMode() {
  isMarketSelectMode = !isMarketSelectMode;
  const selectBtn = document.getElementById("btn-select-markets");
  const selectAllBtn = document.getElementById("btn-select-all-markets");
  const blockBtn = document.getElementById("btn-apply-bulk-block");
  const reduceBtn = document.getElementById("btn-apply-bulk-reduce");

  if (isMarketSelectMode) {
    if (selectBtn) {
      selectBtn.innerHTML = "❌ Cancelar Selección";
      selectBtn.style.background = "rgba(239, 68, 68, 0.15)";
      selectBtn.style.borderColor = "var(--red)";
      selectBtn.style.color = "var(--red)";
    }
    if (selectAllBtn) selectAllBtn.style.display = "inline-flex";
    if (blockBtn) blockBtn.style.display = "inline-flex";
    if (reduceBtn) reduceBtn.style.display = "inline-flex";
  } else {
    selectedMarketsSet.clear();
    if (selectBtn) {
      selectBtn.innerHTML = "☑️ Seleccionar";
      selectBtn.style.background = "rgba(99, 102, 241, 0.15)";
      selectBtn.style.borderColor = "var(--accent)";
      selectBtn.style.color = "var(--accent-light)";
    }
    if (selectAllBtn) selectAllBtn.style.display = "none";
    if (blockBtn) blockBtn.style.display = "none";
    if (reduceBtn) reduceBtn.style.display = "none";
  }
  updateBulkGovernanceButtons();
  renderFilteredMatches();
}

function toggleMarketSelection(marketName, isChecked) {
  if (isChecked) {
    selectedMarketsSet.add(marketName);
  } else {
    selectedMarketsSet.delete(marketName);
  }
  updateBulkGovernanceButtons();
  renderFilteredMatches();
}

function toggleSelectAllMarkets() {
  if (!currentMarketsList || currentMarketsList.length === 0) return;
  const allSelected = currentMarketsList.every((m) =>
    selectedMarketsSet.has(m.name),
  );
  if (allSelected) {
    selectedMarketsSet.clear();
  } else {
    currentMarketsList.forEach((m) => selectedMarketsSet.add(m.name));
  }
  updateBulkGovernanceButtons();
  renderFilteredMatches();
}

function updateBulkGovernanceButtons() {
  const blockBtn = document.getElementById("btn-apply-bulk-block");
  const reduceBtn = document.getElementById("btn-apply-bulk-reduce");
  const selectAllBtn = document.getElementById("btn-select-all-markets");
  if (!blockBtn && !reduceBtn) return;

  const count = selectedMarketsSet.size;
  if (blockBtn) blockBtn.textContent = `🚫 Blacklist (${count})`;
  if (reduceBtn) reduceBtn.textContent = `📉 Reducir Stake (${count})`;

  [blockBtn, reduceBtn].forEach((btn) => {
    if (!btn) return;
    if (count > 0) {
      btn.disabled = false;
      btn.style.opacity = "1";
      btn.style.cursor = "pointer";
    } else {
      btn.disabled = true;
      btn.style.opacity = "0.6";
      btn.style.cursor = "not-allowed";
    }
  });

  if (selectAllBtn && currentMarketsList.length > 0) {
    const allSelected = currentMarketsList.every((m) =>
      selectedMarketsSet.has(m.name),
    );
    selectAllBtn.textContent = allSelected
      ? "Deseleccionar Todos"
      : "Seleccionar Todos";
  }
}

async function applyBulkGovernance(action) {
  if (!activeLeague || selectedMarketsSet.size === 0) return;
  const count = selectedMarketsSet.size;
  const actionLabel =
    action === "block" ? "agregar a la blacklist" : "reducir stake de";
  if (
    !confirm(
      `¿Deseas ${actionLabel} los ${count} mercados seleccionados para "${activeLeague}"?`,
    )
  ) {
    return;
  }

  try {
    const endpoint =
      action === "block"
        ? "/api/v1/leagues/blacklist-markets"
        : "/api/v1/leagues/governance/batch-action";
    const body =
      action === "block"
        ? { league: activeLeague, markets: Array.from(selectedMarketsSet) }
        : {
            league: activeLeague,
            markets: Array.from(selectedMarketsSet),
            action: action,
            stake_multiplier: 0.5,
          };

    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    alert(data.message || "Acción completada con éxito.");

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
    const blockBtn = document.getElementById("btn-apply-bulk-block");
    if (blockBtn) blockBtn.style.display = "none";
    const reduceBtn = document.getElementById("btn-apply-bulk-reduce");
    if (reduceBtn) reduceBtn.style.display = "none";

    await fetchLeagues();
  } catch (err) {
    console.error("Error en gobernanza en lote:", err);
    alert("Error al aplicar la acción de gobernanza: " + err.message);
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
      `¿Deseas agregar el mercado "${marketName}" a la blacklist de "${activeLeague}"?`,
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
    alert(data.message || "Mercado añadido a la blacklist.");

    // Recargar ligas para refrescar rentabilidades manteniendo la liga activa seleccionada
    await fetchLeagues();
  } catch (err) {
    console.error("Error al agregar mercado a la blacklist:", err);
    alert("Error al agregar a la blacklist: " + err.message);
  }
}

async function reduceMarketStake(marketName) {
  if (!activeLeague) return;
  if (
    !confirm(
      `¿Deseas reducir el stake (50%) para el mercado "${marketName}" en la gobernanza de "${activeLeague}"?`,
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
