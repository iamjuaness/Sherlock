// leagues.js - Control de la sección de ligas en Sherlock
let leaguesData = [];
let activeLeague = null;

document.addEventListener("DOMContentLoaded", () => {
  fetchLeagues();
});

async function fetchLeagues() {
  try {
    const res = await fetch("/api/v1/stats/leagues");
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
      const profitClass =
        league.total_profit >= 0 ? "profit--positive" : "profit--negative";
      const profitSign = league.total_profit >= 0 ? "+" : "";
      return `
      <div class="league-list-item ${activeClass}" onclick="selectLeague('${escapeAttr(league.name)}')">
        <span class="league-list-item__name" title="${escapeHtml(league.name)}">🏆 ${escapeHtml(league.name)}</span>
        <span class="league-list-item__profit ${profitClass}">${profitSign}${league.total_profit.toFixed(2)}u</span>
      </div>
    `;
    })
    .join("");
}

function selectLeague(name) {
  activeLeague = name;
  renderLeaguesList();

  const leagueInfo = leaguesData.find((l) => l.name === name);
  if (!leagueInfo) return;

  // Render stats
  document.getElementById("selected-league-name").textContent = leagueInfo.name;
  document.getElementById("lbl-total-matches").textContent =
    leagueInfo.total_matches;
  document.getElementById("lbl-total-picks").textContent =
    leagueInfo.total_picks;
  document.getElementById("lbl-accuracy").textContent =
    `${leagueInfo.accuracy}%`;

  const profitEl = document.getElementById("lbl-profit");
  profitEl.textContent = `${leagueInfo.total_profit >= 0 ? "+" : ""}${leagueInfo.total_profit.toFixed(2)} u`;
  profitEl.style.color =
    leagueInfo.total_profit >= 0 ? "var(--green)" : "var(--red)";

  fetchMatchesForLeague(name);
}

async function fetchMatchesForLeague(name) {
  const matchesContainer = document.getElementById("matches-list");
  if (!matchesContainer) return;

  matchesContainer.innerHTML = `<div class="dashboard-loader"><div class="spinner"></div><span>Cargando partidos...</span></div>`;

  try {
    const res = await fetch(
      `/api/v1/analysis?competition=${encodeURIComponent(name)}`,
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const matches = await res.json();

    if (matches.length === 0) {
      matchesContainer.innerHTML = `<div style="color: var(--text-muted); padding: 2rem; text-align: center;">No hay partidos registrados.</div>`;
      return;
    }

    const cards = matches.map((match) => {
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
        (p) =>
          p.is_publishable ||
          p.is_underdog ||
          p.is_high_confidence ||
          p.is_value,
      );

      // Calculate total match profit/units considering all visible picks
      let totalProfit = 0;
      let hasResolvedPicks = false;
      visiblePicks.forEach((pick) => {
        const sel = pick.selection || "";
        const odds = typeof pick.odds === "number" ? pick.odds : parseFloat(pick.odds) || 0;
        let success = pick.success;
        if (success === undefined || success === null) {
          success = successMap[sel.toLowerCase()];
        }
        if (success === true) {
          totalProfit += (odds - 1);
          hasResolvedPicks = true;
        } else if (success === false) {
          totalProfit -= 1;
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
            } else {
              badge = `<span class="badge-pending">⏳ Pendiente</span>`;
            }

            // Category badge
            let catBadge = "";
            if (pick.is_high_confidence) {
              catBadge =
                '<span style="font-size:0.7rem; color:#f59e0b; margin-left:4px;">🔥 HC</span>';
            } else if (pick.is_underdog) {
              catBadge =
                '<span style="font-size:0.7rem; color:#a78bfa; margin-left:4px;">🐕 Dog</span>';
            } else if (pick.is_publishable || pick.is_value) {
              catBadge =
                '<span style="font-size:0.7rem; color:#60a5fa; margin-left:4px;">🎯 Pro</span>';
            }

            return `
            <div class="pick-row">
              <div style="display:flex; align-items:center; gap:4px; flex-wrap:wrap;">
                <span style="font-weight: 600; color: #fff;">${escapeHtml(sel)}</span>
                ${catBadge}
                <span style="color: var(--text-muted); font-size: 0.8rem;">@${odds.toFixed(2)}</span>
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
              <span class="match-card__title">${escapeHtml(match.match_title)}</span>${matchUnitsText}
              ${statsBadge}
            </div>
            <div style="display: flex; align-items: center; gap: 1rem;">
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
  } catch (error) {
    console.error("Error cargando partidos:", error);
    matchesContainer.innerHTML = `<div style="color: var(--red); padding: 2rem; text-align: center;">❌ Error al cargar partidos: ${escapeHtml(error.message)}</div>`;
  }
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
