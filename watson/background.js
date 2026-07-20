// background.js - Service Worker de Watson (SofaScore Extractor)
// Versión corregida con standings reales

importScripts("sofaScoreToSherlock.js");

// ═══════════════════════════════════════════════════════════════
// INSTALACIÓN
// ═══════════════════════════════════════════════════════════════
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    chrome.storage.sync.set({
      endpointUrl: "http://localhost:8000/api/v1/prefill",
      authToken: "",
      extractLineups: true,
      extractStreaks: true,
      extractHomeStats: true,
      extractAwayStats: true,
      extractIncidents: false,
      extractHeatmaps: false,
      autoSend: "never",
    });
    chrome.runtime.openOptionsPage();
  }
});

// ═══════════════════════════════════════════════════════════════
// MENSAJES
// ═══════════════════════════════════════════════════════════════
// Flag para cancelar extracción histórica
let _historicalCancelled = false;

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "extractStats") {
    handleExtractStats(request.data)
      .then(sendResponse)
      .catch((err) => {
        sendResponse({ success: false, error: err.message });
      });
    return true;
  }

  if (request.action === "sendToEndpoint") {
    handleSendToEndpoint(request.data)
      .then(sendResponse)
      .catch((err) => {
        sendResponse({ success: false, error: err.message });
      });
    return true;
  }

  if (request.action === "extractResults") {
    handleExtractResults(request.data)
      .then(sendResponse)
      .catch((err) => {
        sendResponse({ success: false, error: err.message });
      });
    return true;
  }

  if (request.action === "extractHistoricalData") {
    _historicalCancelled = false;
    handleExtractHistoricalData(request.data)
      .then(sendResponse)
      .catch((err) => {
        sendResponse({ success: false, error: err.message });
      });
    return true;
  }

  if (request.action === "cancelHistoricalExtraction") {
    _historicalCancelled = true;
    sendResponse({ success: true });
    return true;
  }
});

// ═══════════════════════════════════════════════════════════════
// EXTRACCIÓN DE RESULTADOS
// ═══════════════════════════════════════════════════════════════
async function handleExtractResults(data) {
  try {
    const { eventId } = data;
    const settings = await chrome.storage.sync.get(["endpointUrl"]);
    if (!settings.endpointUrl) {
      throw new Error("Endpoint no configurado");
    }

    let baseUrl = settings.endpointUrl;
    if (baseUrl.includes("/api/v1")) {
      baseUrl = baseUrl.split("/api/v1")[0];
    }

    // 1. Fetch Event Info
    const eventData = await fetchSofaScore(`/api/v1/event/${eventId}`);
    if (!eventData || !eventData.event)
      throw new Error("No se pudo obtener el evento");

    // 2. Fetch Statistics
    let statisticsData = null;
    try {
      statisticsData = await fetchSofaScore(
        `/api/v1/event/${eventId}/statistics`,
      );
    } catch (e) {
      console.warn("No statistics", e.message);
    }

    // 3. Fetch Incidents
    let incidentsData = null;
    try {
      incidentsData = await fetchSofaScore(
        `/api/v1/event/${eventId}/incidents`,
      );
    } catch (e) {
      console.warn("No incidents", e.message);
    }

    // 4. Parse results
    const payload = {
      final_score_home: eventData.event.homeScore?.current || 0,
      final_score_away: eventData.event.awayScore?.current || 0,
    };

    if (statisticsData && statisticsData.statistics) {
      const statPeriod = getStatsPeriod(statisticsData);
      if (statPeriod) {
        applyStatsToPayload(statPeriod, payload);
      }
    }

    if (incidentsData && incidentsData.incidents) {
      let rcHome = 0;
      let rcAway = 0;
      incidentsData.incidents.forEach((inc) => {
        if (inc.incidentType === "card" && inc.incidentClass === "red") {
          if (inc.isHome) rcHome++;
          else rcAway++;
        }
      });
      payload.final_red_cards_home = rcHome;
      payload.final_red_cards_away = rcAway;
    }

    // 5. Enviar al endpoint de resultados de Sherlock
    const resPush = await fetch(`${baseUrl}/api/v1/result`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sport: "football",
        home_team: eventData.event.homeTeam.name,
        away_team: eventData.event.awayTeam.name,
        ...payload,
      }),
    });

    if (!resPush.ok) {
      throw new Error(`Error en el servidor al enviar: ${resPush.status}`);
    }

    const resData = await resPush.json();

    return {
      success: true,
      message: resData.message || "Resultados enviados correctamente",
    };
  } catch (error) {
    console.error("Error en extractResults:", error);
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════
// EXTRACCIÓN PRINCIPAL
// ═══════════════════════════════════════════════════════════════
async function handleExtractStats(data) {
  try {
    const { eventId, homeTeamId, awayTeamId, tournamentId, seasonId } = data;
    const settings = await chrome.storage.sync.get([
      "extractLineups",
      "extractStreaks",
      "extractHomeStats",
      "extractAwayStats",
      "extractIncidents",
      "extractHeatmaps",
    ]);

    const result = {
      metadata: {
        extractedAt: new Date().toISOString(),
        source: "sofascore.com",
        eventId,
        url: data.url,
      },
      match: null,
      lineups: null,
      teamStreaks: null,
      incidents: null,
      homeTeamStats: null,
      awayTeamStats: null,
      standings: null, // ← NUEVO: standings del torneo
    };

    // 1. Info del evento
    const eventData = await fetchSofaScore(`/api/v1/event/${eventId}`);
    result.match = eventData.event;

    // 2. STANDINGS (para wins/draws/losses reales)
    if (tournamentId && seasonId) {
      try {
        result.standings = await fetchSofaScore(
          `/api/v1/tournament/${tournamentId}/season/${seasonId}/standings/total`,
        );
      } catch (e) {
        console.warn("Standings:", e.message);
      }
      try {
        result.leagueInfo = await fetchSofaScore(
          `/api/v1/unique-tournament/${tournamentId}/season/${seasonId}/info`,
        );
      } catch (e) {
        console.warn("League info:", e.message);
      }
    }

    // 3. Alineaciones
    if (settings.extractLineups) {
      try {
        result.lineups = await fetchSofaScore(
          `/api/v1/event/${eventId}/lineups`,
        );
      } catch (e) {
        console.warn("Lineups:", e.message);
      }
    }

    // 4. Streaks
    if (settings.extractStreaks) {
      try {
        result.teamStreaks = await fetchSofaScore(
          `/api/v1/event/${eventId}/team-streaks`,
        );
      } catch (e) {
        console.warn("Streaks:", e.message);
      }
    }

    // 5. Incidentes
    if (settings.extractIncidents) {
      try {
        result.incidents = await fetchSofaScore(
          `/api/v1/event/${eventId}/incidents`,
        );
      } catch (e) {
        console.warn("Incidents:", e.message);
      }
    }

    // 6. Stats equipo local
    if (settings.extractHomeStats && homeTeamId && tournamentId && seasonId) {
      try {
        result.homeTeamStats = await fetchSofaScore(
          `/api/v1/team/${homeTeamId}/unique-tournament/${tournamentId}/season/${seasonId}/statistics/overall`,
        );
      } catch (e) {
        console.warn("Home stats:", e.message);
      }
    }

    // 7. Stats equipo visitante
    if (settings.extractAwayStats && awayTeamId && tournamentId && seasonId) {
      try {
        result.awayTeamStats = await fetchSofaScore(
          `/api/v1/team/${awayTeamId}/unique-tournament/${tournamentId}/season/${seasonId}/statistics/overall`,
        );
      } catch (e) {
        console.warn("Away stats:", e.message);
      }
    }

    // Guardar resultado
    await chrome.storage.local.set({
      lastExtractedStats: result,
      lastExtractedAt: Date.now(),
    });

    // Auto-send
    const autoSend = (await chrome.storage.sync.get(["autoSend"])).autoSend;
    if (autoSend === "after_extract") {
      await handleSendToEndpoint(result);
    }

    return { success: true, data: result };
  } catch (error) {
    console.error("Error en extracción:", error);
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════
// ENVÍO AL ENDPOINT
// ═══════════════════════════════════════════════════════════════
async function handleSendToEndpoint(data) {
  const settings = await chrome.storage.sync.get(["endpointUrl", "authToken"]);

  if (!settings.endpointUrl) {
    return { success: false, error: "Endpoint no configurado" };
  }

  let endpointUrl = settings.endpointUrl;
  if (endpointUrl && !endpointUrl.includes("/api/v1/prefill")) {
    endpointUrl = endpointUrl.replace(/\/+$/, "") + "/api/v1/prefill";
  }

  let payload;
  try {
    payload = buildSherlockPayload(data);
  } catch (error) {
    return { success: false, error: `Error mapeando datos: ${error.message}` };
  }

  const headers = {
    "Content-Type": "application/json",
    "X-Source": "sofascore-extractor",
    "X-Extractor-Version": "1.1.0",
    "X-Event-Id": data.metadata?.eventId || "unknown",
  };

  if (settings.authToken) {
    headers["Authorization"] =
      settings.authToken.startsWith("Bearer") ||
      settings.authToken.startsWith("Basic")
        ? settings.authToken
        : `Bearer ${settings.authToken}`;
  }

  try {
    const response = await fetch(endpointUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    return {
      success: response.ok,
      status: response.status,
      statusText: response.statusText,
    };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// ═══════════════════════════════════════════════════════════════
// HELPER FETCH
// ═══════════════════════════════════════════════════════════════
async function fetchSofaScore(path) {
  const url = `https://www.sofascore.com${path}`;
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
      "X-Requested-With": "XMLHttpRequest",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status} en ${path}`);
  }

  return await response.json();
}

// ═══════════════════════════════════════════════════════════════
// UTILIDADES DE ESTADÍSTICAS
// ═══════════════════════════════════════════════════════════════

/** Elige el período correcto: suma 1ST+2ND si existen, sino usa ALL */
function getStatsPeriod(statisticsData) {
  if (!statisticsData || !statisticsData.statistics) return null;
  const firstHalf = statisticsData.statistics.find((s) => s.period === "1ST");
  const secondHalf = statisticsData.statistics.find((s) => s.period === "2ND");
  const allPeriod =
    statisticsData.statistics.find((s) => s.period === "ALL") ||
    statisticsData.statistics[0];

  if (firstHalf && secondHalf) {
    return mergeStatsPeriods(firstHalf, secondHalf);
  }
  return allPeriod || null;
}

// Keys que deben promediarse (no sumarse) entre mitades
const PERCENTAGE_KEYS = new Set([
  "ballPossession",
  "aerialDuelsPercentage",
  "groundDuelsPercentage",
  "dribblesPercentage",
  "duelWonPercent",
  "wonTacklePercent",
  "expectedGoals",
]);

/** Fusiona dos períodos sumando valores numéricos (promedia los porcentajes) */
function mergeStatsPeriods(p1, p2) {
  const groups2Map = new Map((p2.groups || []).map((g) => [g.groupName, g]));
  const mergedGroups = (p1.groups || []).map((g1) => {
    const g2 = groups2Map.get(g1.groupName) || { statisticsItems: [] };
    const items2Map = new Map(
      (g2.statisticsItems || []).map((i) => [i.key, i]),
    );
    const mergedItems = (g1.statisticsItems || []).map((i1) => {
      const i2 = items2Map.get(i1.key);
      const h1 = parseFloat(i1.homeValue) || 0;
      const a1 = parseFloat(i1.awayValue) || 0;
      const h2 = i2 ? parseFloat(i2.homeValue) || 0 : 0;
      const a2 = i2 ? parseFloat(i2.awayValue) || 0 : 0;
      const isPercent = PERCENTAGE_KEYS.has(i1.key);
      return {
        ...i1,
        homeValue: String(isPercent ? (h1 + h2) / 2 : h1 + h2),
        awayValue: String(isPercent ? (a1 + a2) / 2 : a1 + a2),
      };
    });
    return { ...g1, statisticsItems: mergedItems };
  });
  return { ...p1, groups: mergedGroups };
}

/** Aplica todos los keys de estadísticas al payload (home/away) */
function applyStatsToPayload(statPeriod, payload) {
  const STAT_MAP = {
    // Keys del planning.txt
    accurateCross: ["accurate_cross_home", "accurate_cross_away"],
    accurateLongBalls: ["accurate_long_balls_home", "accurate_long_balls_away"],
    accuratePasses: ["accurate_passes_home", "accurate_passes_away"],
    accurateThroughBall: [
      "accurate_through_ball_home",
      "accurate_through_ball_away",
    ],
    aerialDuelsPercentage: [
      "aerial_duels_percentage_home",
      "aerial_duels_percentage_away",
    ],
    ballPossession: ["ball_possession_home", "ball_possession_away"],
    ballRecovery: ["ball_recovery_home", "ball_recovery_away"],
    bigChanceCreated: ["big_chance_created_home", "big_chance_created_away"],
    bigChanceMissed: ["big_chance_missed_home", "big_chance_missed_away"],
    bigChanceScored: ["big_chance_scored_home", "big_chance_scored_away"],
    blockedScoringAttempt: [
      "blocked_scoring_attempt_home",
      "blocked_scoring_attempt_away",
    ],
    cornerKicks: ["corner_kicks_home", "corner_kicks_away"],
    dispossessed: ["dispossessed_home", "dispossessed_away"],
    diveSaves: ["dive_saves_home", "dive_saves_away"],
    duelWonPercent: ["duel_won_percent_home", "duel_won_percent_away"],
    dribblesPercentage: [
      "dribbles_percentage_home",
      "dribbles_percentage_away",
    ],
    expectedGoals: ["expected_goals_home", "expected_goals_away"],
    finalThirdEntries: ["final_third_entries_home", "final_third_entries_away"],
    finalThirdPhaseStatistic: [
      "final_third_phase_statistic_home",
      "final_third_phase_statistic_away",
    ],
    fouledFinalThird: ["fouled_final_third_home", "fouled_final_third_away"],
    fouls: ["fouls_home", "fouls_away"],
    freeKicks: ["free_kicks_home", "free_kicks_away"],
    goalKicks: ["goal_kicks_home", "goal_kicks_away"],
    goalkeeperSaves: ["goalkeeper_saves_home", "goalkeeper_saves_away"],
    goalsPrevented: ["goals_prevented_home", "goals_prevented_away"],
    groundDuelsPercentage: [
      "ground_duels_percentage_home",
      "ground_duels_percentage_away",
    ],
    highClaims: ["high_claims_home", "high_claims_away"],
    hitWoodwork: ["hit_woodwork_home", "hit_woodwork_away"],
    interceptionWon: ["interception_won_home", "interception_won_away"],
    offsides: ["offsides_home", "offsides_away"],
    passes: ["passes_home", "passes_away"],
    punches: ["punches_home", "punches_away"],
    shotsOffGoal: ["shots_off_goal_home", "shots_off_goal_away"],
    shotsOnGoal: ["shots_on_goal_home", "shots_on_goal_away"],
    throwIns: ["throw_ins_home", "throw_ins_away"],
    totalClearance: ["total_clearance_home", "total_clearance_away"],
    totalShotsInsideBox: [
      "total_shots_inside_box_home",
      "total_shots_inside_box_away",
    ],
    totalShotsOnGoal: ["total_shots_on_goal_home", "total_shots_on_goal_away"],
    totalShotsOutsideBox: [
      "total_shots_outside_box_home",
      "total_shots_outside_box_away",
    ],
    totalTackle: ["total_tackle_home", "total_tackle_away"],
    touchesInOppBox: ["touches_in_opp_box_home", "touches_in_opp_box_away"],
    wonTacklePercent: ["won_tackle_percent_home", "won_tackle_percent_away"],
    yellowCards: ["yellow_cards_home", "yellow_cards_away"],
    // Aliases legacy usados en handleExtractResults
    // (se mantienen los final_* para compatibilidad)
  };

  (statPeriod.groups || []).forEach((group) => {
    (group.statisticsItems || []).forEach((item) => {
      const mapping = STAT_MAP[item.key];
      if (mapping) {
        const [homeKey, awayKey] = mapping;
        const isPercent = PERCENTAGE_KEYS.has(item.key);
        payload[homeKey] = isPercent
          ? parseFloat(item.homeValue) || 0
          : parseInt(item.homeValue) || 0;
        payload[awayKey] = isPercent
          ? parseFloat(item.awayValue) || 0
          : parseInt(item.awayValue) || 0;
      }
      // Legacy aliases
      if (item.key === "cornerKicks") {
        payload.final_corners_home = parseInt(item.homeValue) || 0;
        payload.final_corners_away = parseInt(item.awayValue) || 0;
      }
      if (item.key === "yellowCards") {
        payload.final_yellow_cards_home = parseInt(item.homeValue) || 0;
        payload.final_yellow_cards_away = parseInt(item.awayValue) || 0;
      }
      if (item.key === "totalShotsOnGoal" || item.key === "totalShots") {
        payload.final_shots_home = parseInt(item.homeValue) || 0;
        payload.final_shots_away = parseInt(item.awayValue) || 0;
      }
      if (item.key === "shotsOnGoal") {
        payload.final_shots_on_target_home = parseInt(item.homeValue) || 0;
        payload.final_shots_on_target_away = parseInt(item.awayValue) || 0;
      }
      if (item.key === "fouls") {
        payload.final_fouls_home = parseInt(item.homeValue) || 0;
        payload.final_fouls_away = parseInt(item.awayValue) || 0;
      }
      if (item.key === "offsides") {
        payload.final_offsides_home = parseInt(item.homeValue) || 0;
        payload.final_offsides_away = parseInt(item.awayValue) || 0;
      }
    });
  });
}

// ═══════════════════════════════════════════════════════════════
// EXTRACCIÓN HISTÓRICA DE COMPETICIÓN
// ═══════════════════════════════════════════════════════════════

/** Pequeño delay para evitar bloqueo de IP */
function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Envía progreso al popup (fire-and-forget) */
function sendProgress(progressData) {
  chrome.runtime
    .sendMessage({ action: "historicalProgress", data: progressData })
    .catch(() => {});
}

async function handleExtractHistoricalData(data) {
  const { tournamentId, tournamentName, baseUrl } = data;

  if (!baseUrl) throw new Error("Endpoint de Sherlock no configurado");
  if (!tournamentId) throw new Error("ID de competición no encontrado");

  // ── 0. Cargar estado previo (para poder reanudar) ──────────────────────
  const masterKey = `tournament_${tournamentId}_events`;
  const completedKey = `tournament_${tournamentId}_completed_seasons`;

  const storedState = await chrome.storage.local.get([masterKey, completedKey]);
  // Temporadas ya completadas en ejecuciones anteriores
  const completedSeasons = new Set(storedState[completedKey] || []);
  // Eventos acumulados de ejecuciones previas
  const allEvents = storedState[masterKey] || [];

  const completedCount = completedSeasons.size;

  // ── 1. Obtener temporadas ──────────────────────────────────────────────
  sendProgress({ phase: "seasons", message: "Obteniendo temporadas..." });
  const seasonsData = await fetchSofaScore(
    `/api/v1/unique-tournament/${tournamentId}/seasons`,
  );
  if (!seasonsData || !seasonsData.seasons)
    throw new Error("No se pudieron obtener las temporadas");

  const seasons = seasonsData.seasons;
  const pendingCount = seasons.filter(
    (s) => !completedSeasons.has(String(s.id)),
  ).length;

  sendProgress({
    phase: "seasons",
    message: `${seasons.length} temporadas — ${completedCount} ya completadas, ${pendingCount} pendientes`,
    totalSeasons: seasons.length,
    completedSeasons: completedCount,
  });

  let totalProcessed = 0;
  let totalSaved = 0;
  let totalErrors = 0;

  // ── 2. Iterar temporadas ───────────────────────────────────────────────
  for (let si = 0; si < seasons.length; si++) {
    if (_historicalCancelled) {
      sendProgress({
        phase: "cancelled",
        message: "Extracción cancelada — el progreso está guardado",
      });
      return {
        success: false,
        cancelled: true,
        totalProcessed,
        totalSaved,
        totalErrors,
      };
    }

    const season = seasons[si];
    const seasonKey = String(season.id);

    // ── ¿Esta temporada ya fue completada? ────────────────────────────
    if (completedSeasons.has(seasonKey)) {
      sendProgress({
        phase: "season_skipped",
        seasonIndex: si,
        totalSeasons: seasons.length,
        seasonYear: season.year,
        message: `⏭ T.${season.year} ya completada — saltando`,
      });
      continue; // Los eventos ya están en allEvents desde el storage
    }

    sendProgress({
      phase: "season_start",
      seasonIndex: si,
      totalSeasons: seasons.length,
      seasonYear: season.year,
      seasonId: season.id,
      message: `Temporada ${season.year} (${si + 1}/${seasons.length})`,
    });

    // ── 3. Paginar eventos de la temporada ────────────────────────────
    let page = 0;
    let hasNextPage = true;
    const seasonEvents = [];

    while (hasNextPage) {
      if (_historicalCancelled) break;

      try {
        const eventsData = await fetchSofaScore(
          `/api/v1/unique-tournament/${tournamentId}/season/${season.id}/events/last/${page}`,
        );
        const events = eventsData.events || [];
        hasNextPage = eventsData.hasNextPage === true;

        const finished = events.filter(
          (e) => e.status && e.status.type === "finished",
        );
        seasonEvents.push(...finished);

        sendProgress({
          phase: "fetching_events",
          seasonYear: season.year,
          seasonIndex: si,
          totalSeasons: seasons.length,
          page,
          eventsInPage: events.length,
          finishedInPage: finished.length,
          totalSeasonEvents: seasonEvents.length,
          message: `T.${season.year} — pág ${page}: ${finished.length} partidos finalizados`,
        });

        page++;
        await delay(600);
      } catch (e) {
        console.warn(`Error en pág ${page} de temp ${season.year}:`, e.message);
        hasNextPage = false;
      }
    }

    // ── Sin eventos en esta temporada → terminar anticipadamente ────────
    if (seasonEvents.length === 0 && !_historicalCancelled) {
      // Determinar la última temporada que sí tuvo datos
      const lastSavedSeason = si > 0 ? seasons[si - 1].year : null;
      const msg = lastSavedSeason
        ? `⛔ T.${season.year} sin datos — proceso detenido. Última temporada guardada: T.${lastSavedSeason}`
        : `⛔ T.${season.year} sin datos y es la primera temporada — no se guardó nada`;

      sendProgress({
        phase: "no_data_stop",
        seasonYear: season.year,
        lastSavedSeasonYear: lastSavedSeason,
        totalSaved,
        totalErrors,
        message: msg,
      });

      break; // Las temporadas anteriores tampoco tendrán datos
    }

    // Enriquecer con metadatos de temporada
    const enrichedSeasonEvents = seasonEvents.map((e) => ({
      ...e,
      _seasonYear: season.year,
      _seasonId: season.id,
    }));

    // ── 4. Procesar cada evento de la temporada ───────────────────────
    let seasonSaved = 0;
    let seasonErrors = 0;

    for (let ei = 0; ei < enrichedSeasonEvents.length; ei++) {
      if (_historicalCancelled) break;

      const event = enrichedSeasonEvents[ei];
      totalProcessed++;

      sendProgress({
        phase: "processing_event",
        seasonYear: season.year,
        seasonIndex: si,
        totalSeasons: seasons.length,
        eventIndex: ei,
        totalSeasonEvents: enrichedSeasonEvents.length,
        eventId: event.id,
        homeTeam: event.homeTeam?.name,
        awayTeam: event.awayTeam?.name,
        totalProcessed,
        totalSaved,
        message: `${event.homeTeam?.name} vs ${event.awayTeam?.name}`,
      });

      try {
        let statisticsData = null;
        try {
          statisticsData = await fetchSofaScore(
            `/api/v1/event/${event.id}/statistics`,
          );
        } catch (e) {
          /* sin stats */
        }
        await delay(300);

        let incidentsData = null;
        try {
          incidentsData = await fetchSofaScore(
            `/api/v1/event/${event.id}/incidents`,
          );
        } catch (e) {
          /* sin incidentes */
        }
        await delay(300);

        const payload = buildHistoricalPayload(
          event,
          statisticsData,
          incidentsData,
          tournamentName,
        );

        const res = await fetch(`${baseUrl}/api/v1/result`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (res.ok) {
          totalSaved++;
          seasonSaved++;
        } else {
          totalErrors++;
          seasonErrors++;
          console.warn(`Error guardando evento ${event.id}: ${res.status}`);
        }
      } catch (e) {
        totalErrors++;
        seasonErrors++;
        console.warn(`Error procesando evento ${event.id}:`, e.message);
      }
    }

    // ── 5. Guardar progreso de esta temporada (aunque esté cancelada) ──
    // Solo marcar como completada si NO fue interrumpida a mitad
    const seasonWasCancelled =
      _historicalCancelled &&
      seasonErrors === 0 &&
      enrichedSeasonEvents.length > 0;

    if (!_historicalCancelled || seasonWasCancelled === false) {
      // Agregar eventos de esta temporada al array maestro
      // Evitar duplicados por si hay eventos ya cargados de ejecuciones previas
      const existingIds = new Set(allEvents.map((e) => e.id));
      const newEvents = enrichedSeasonEvents.filter(
        (e) => !existingIds.has(e.id),
      );
      allEvents.push(...newEvents);

      // Guardar en storage: temporada individual + lista maestra + temporadas completadas
      const seasonStorageKey = `tournament_${tournamentId}_season_${season.id}_events`;
      completedSeasons.add(seasonKey);

      await chrome.storage.local.set({
        [seasonStorageKey]: enrichedSeasonEvents,
        [masterKey]: allEvents,
        [completedKey]: Array.from(completedSeasons),
        [`tournament_${tournamentId}_lastSync`]: Date.now(),
      });

      sendProgress({
        phase: "season_saved",
        seasonYear: season.year,
        seasonIndex: si,
        totalSeasons: seasons.length,
        seasonSaved,
        seasonErrors,
        totalSaved,
        totalErrors,
        message: `✅ T.${season.year} guardada: ${seasonSaved} OK, ${seasonErrors} errores`,
        allEvents,
      });
    }

    if (!_historicalCancelled && si < seasons.length - 1) {
      await delay(1000); // Espera entre temporadas
    }
  }

  // ── 6. Señal final ─────────────────────────────────────────────────────
  // Determinar la última temporada que efectivamente se guardó
  const lastSavedIdx =
    [...completedSeasons].length > 0
      ? seasons.findIndex((s) => completedSeasons.has(String(s.id)))
      : -1;
  // El array de temporadas viene ordenado de más reciente a más antigua;
  // la última completada en orden de iteración es la de índice más alto.
  const lastCompletedSeason = seasons
    .filter((s) => completedSeasons.has(String(s.id)))
    .at(-1);

  sendProgress({
    phase: "done",
    message: `Completado: ${totalSaved} guardados, ${totalErrors} errores${
      lastCompletedSeason ? ` — hasta T.${lastCompletedSeason.year}` : ""
    }`,
    totalProcessed,
    totalSaved,
    totalErrors,
    lastSavedSeasonYear: lastCompletedSeason?.year ?? null,
    allEvents,
  });

  return { success: true, totalProcessed, totalSaved, totalErrors };
}

/** Construye el payload histórico con todos los campos del planning */
function buildHistoricalPayload(
  event,
  statisticsData,
  incidentsData,
  tournamentName,
) {
  const payload = {
    sport: "football",
    home_team: event.homeTeam?.name || "",
    away_team: event.awayTeam?.name || "",
    event_id: event.id,
    round: event.roundInfo?.round || null,
    start_timestamp: event.startTimestamp || null,
    season_year: event._seasonYear || null,
    season_id: event._seasonId || null,
    tournament_id: event.tournament?.uniqueTournament?.id || null,
    tournament_name:
      tournamentName ||
      event.tournament?.uniqueTournament?.name ||
      event.tournament?.name ||
      null,
    competition:
      tournamentName ||
      event.tournament?.uniqueTournament?.name ||
      event.tournament?.name ||
      null,
    final_score_home: event.homeScore?.current ?? 0,
    final_score_away: event.awayScore?.current ?? 0,
  };

  // Stats del partido
  if (statisticsData && statisticsData.statistics) {
    const statPeriod = getStatsPeriod(statisticsData);
    if (statPeriod) {
      applyStatsToPayload(statPeriod, payload);
    }
  }

  // Tarjetas rojas desde incidentes
  if (incidentsData && incidentsData.incidents) {
    let rcHome = 0,
      rcAway = 0;
    incidentsData.incidents.forEach((inc) => {
      if (inc.incidentType === "card" && inc.incidentClass === "red") {
        if (inc.isHome) rcHome++;
        else rcAway++;
      }
    });
    payload.red_cards_home = rcHome;
    payload.red_cards_away = rcAway;
    payload.final_red_cards_home = rcHome;
    payload.final_red_cards_away = rcAway;
  }

  return payload;
}

// ═══════════════════════════════════════════════════════════════
// AUTO-DETECT EN CAMBIO DE PESTAÑA
// ═══════════════════════════════════════════════════════════════
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.url && changeInfo.url.includes("sofascore.com")) {
    const eventId = extractEventIdFromUrl(changeInfo.url);
    if (eventId) {
      const autoSend = (await chrome.storage.sync.get(["autoSend"])).autoSend;
      if (autoSend === "on_detect") {
        setTimeout(async () => {
          try {
            chrome.scripting.executeScript(
              {
                target: { tabId },
                func: () => ({
                  url: window.location.href,
                  title: document.title,
                }),
              },
              async (results) => {
                if (results && results[0]) {
                  // TODO: Auto-detect & send
                }
              },
            );
          } catch (e) {
            console.warn("Auto-detect error:", e);
          }
        }, 2000);
      }
    }
  }
});

function extractEventIdFromUrl(url) {
  let match = url.match(/#id:(\d+)/);
  if (match) return match[1];
  match = url.match(/\/event\/(\d+)/);
  if (match) return match[1];
  match = url.match(/[?#&]id[=:](\d+)/);
  if (match) return match[1];
  return null;
}

function safeDiv(a, b) {
  return b > 0 ? a / b : 0;
}
