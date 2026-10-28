// popup.js - Popup de Watson (SofaScore Extractor) con integración Sherlock
// ═══════════════════════════════════════════════════════════════
// ESTADO GLOBAL
// ═══════════════════════════════════════════════════════════════
let currentEventId = null;
let currentUrl = null;
let extractedData = null;
let sherlockEndpoint = "";
let currentMatchData = null;
let isBetanoMode = false;
let betanoOddsPayload = null;
// ═══════════════════════════════════════════════════════════════
// REFERENCIAS DOM
// ═══════════════════════════════════════════════════════════════
const els = {
  matchContainer: document.getElementById("matchContainer"),
  statsContainer: document.getElementById("statsContainer"),
  homeTeam: document.getElementById("homeTeam"),
  awayTeam: document.getElementById("awayTeam"),
  homeTeamId: document.getElementById("homeTeamId"),
  awayTeamId: document.getElementById("awayTeamId"),
  eventId: document.getElementById("eventId"),
  endpointUrl: document.getElementById("endpointUrl"),
  goalsScored: document.getElementById("goalsScored"),
  goalsScoredTeam: document.getElementById("goalsScoredTeam"),
  goalsConceded: document.getElementById("goalsConceded"),
  goalsConcededTeam: document.getElementById("goalsConcededTeam"),
  avgPossession: document.getElementById("avgPossession"),
  avgPossessionTeam: document.getElementById("avgPossessionTeam"),
  shotsOnTarget: document.getElementById("shotsOnTarget"),
  shotsOnTargetTeam: document.getElementById("shotsOnTargetTeam"),
  btnExtract: document.getElementById("btnExtract"),
  btnSend: document.getElementById("btnSend"),
  btnExtractResults: document.getElementById("btnExtractResults"),
  btnViewJson: document.getElementById("btnViewJson"),
  btnSettings: document.getElementById("btnSettings"),
  status: document.getElementById("status"),
  progressBar: document.getElementById("progressBar"),
  progressFill: document.getElementById("progressFill"),
  // Histórico
  historicalContainer: document.getElementById("historicalContainer"),
  competitionName: document.getElementById("competitionName"),
  competitionId: document.getElementById("competitionId"),
  historicalEndpointUrl: document.getElementById("historicalEndpointUrl"),
  historicalCounters: document.getElementById("historicalCounters"),
  cntProcessed: document.getElementById("cntProcessed"),
  cntSaved: document.getElementById("cntSaved"),
  cntErrors: document.getElementById("cntErrors"),
  historicalProgressDetail: document.getElementById("historicalProgressDetail"),
  progressPhase: document.getElementById("progressPhase"),
  progressMessage: document.getElementById("progressMessage"),
  historicalProgressBar: document.getElementById("historicalProgressBar"),
  historicalProgressFill: document.getElementById("historicalProgressFill"),
  btnExtractHistorical: document.getElementById("btnExtractHistorical"),
  btnCancelHistorical: document.getElementById("btnCancelHistorical"),
  btnBulkExtractStats: document.getElementById("btnBulkExtractStats"),
  btnBulkExtractResults: document.getElementById("btnBulkExtractResults"),
  matchesSection: document.getElementById("matchesSection"),
  matchesCount: document.getElementById("matchesCount"),
  matchesToggle: document.getElementById("matchesToggle"),
  matchesSearch: document.getElementById("matchesSearch"),
  matchesList: document.getElementById("matchesList"),
  historicalStatus: document.getElementById("historicalStatus"),
  seasonSelect: document.getElementById("seasonSelect"),
};
// ═══════════════════════════════════════════════════════════════
// INICIALIZACIÓN
// ═══════════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", async () => {
  try {
    // Cargar endpoint configurado
    const settings = await chrome.storage.sync.get(["endpointUrl"]);
    sherlockEndpoint = settings.endpointUrl || "";
    updateEndpointDisplay();
    // Obtener pestaña activa
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });

    // ── Detectar si es URL de Betano ──
    if (tab.url && tab.url.includes("betano.co")) {
      isBetanoMode = true;
      currentUrl = tab.url;
      await showBetanoMode(tab.url);
      return;
    }

    if (!tab.url || !tab.url.includes("sofascore.com")) {
      showNoMatch();
      return;
    }
    currentUrl = tab.url;

    // ── Detectar si es URL de competición ──
    // Las URLs de competición tienen /tournament/ en el path.
    // El #id:XXXX en estas URLs es el seasonId, NO un eventId de partido.
    const tournamentId = extractTournamentIdFromUrl(currentUrl);
    if (tournamentId) {
      await initHistoricalSection(tournamentId, currentUrl);
      setupHistoricalEventListeners();
      return;
    }

    currentEventId = extractEventIdFromUrl(currentUrl);
    if (!currentEventId) {
      showNoMatch();
      return;
    }
    // Cargar info del partido desde la API de SofaScore
    await showMatchInfo(currentEventId, currentUrl);
    // Auto-extracción si hay datos en caché para este evento
    const cached = await chrome.storage.local.get(["lastExtractedStats"]);
    if (
      cached.lastExtractedStats &&
      cached.lastExtractedStats.metadata?.eventId === currentEventId
    ) {
      extractedData = cached.lastExtractedStats;
      showStatsPreview();
    }
    setupEventListeners();
  } catch (error) {
    console.error("Error inicializando popup:", error);
    showNoMatch();
  }
});

// Escuchar mensaje de betano_content.js cuando las cuotas fueron capturadas
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.action === "betanoOddsCaptured" && isBetanoMode) {
    const data = msg.data || {};
    const { homeTeam, awayTeam, payload } = data;
    betanoOddsPayload = payload;

    const matchEl = document.getElementById("betanoMatchName");
    const badgeEl = document.getElementById("betanoBadge");
    const hintEl = document.getElementById("betanoHint");
    const btnSend = document.getElementById("btnSendBetanoOdds");

    if (matchEl && homeTeam) {
      matchEl.textContent = `${homeTeam} vs ${awayTeam}`;
    }
    if (badgeEl) {
      badgeEl.textContent = "Listo para enviar";
      badgeEl.className = "betano-badge scanning";
    }
    if (hintEl) {
      hintEl.textContent =
        "Cuotas cargadas en Watson. Presiona el botón para enviarlas a Sherlock.";
      hintEl.style.color = "#f59e0b";
    }
    if (btnSend) {
      btnSend.disabled = false;
    }
  }
});
// ═══════════════════════════════════════════════════════════════
// EVENT LISTENERS
// ═══════════════════════════════════════════════════════════════
function setupEventListeners() {
  els.btnExtract.addEventListener("click", handleExtract);
  els.btnSend.addEventListener("click", handleSendToSherlock);
  if (els.btnExtractResults) {
    els.btnExtractResults.addEventListener("click", handleExtractResults);
  }
  const btnSaveMatch = document.getElementById("btnSaveMatch");
  if (btnSaveMatch) {
    btnSaveMatch.addEventListener("click", handleSaveMatchWithoutStats);
  }
  if (els.btnBulkExtractStats) {
    els.btnBulkExtractStats.addEventListener("click", handleBulkExtractStatsUI);
  }
  if (els.btnBulkExtractResults) {
    els.btnBulkExtractResults.addEventListener("click", handleBulkExtractResultsUI);
  }
  els.btnViewJson.addEventListener("click", handleViewJson);
  els.btnSettings.addEventListener("click", () =>
    chrome.runtime.openOptionsPage(),
  );
}

// ═══════════════════════════════════════════════════════════════
// EXTRACCIÓN MASIVA (BULK) DE PARTIDOS / RESULTADOS
// ═══════════════════════════════════════════════════════════════
async function getActiveCompetitions() {
  // 1. Intentar consultar las competiciones directamente a la API de Sherlock si el endpoint está configurado
  if (sherlockEndpoint) {
    try {
      let baseUrl = sherlockEndpoint;
      if (baseUrl.includes("/api/v1")) baseUrl = baseUrl.split("/api/v1")[0];
      const res = await fetch(`${baseUrl}/api/v1/competitions`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return data.filter((c) => c.active !== false);
        }
      }
    } catch (e) {
      console.warn("No se pudo obtener competiciones desde la API de Sherlock:", e.message);
    }
  }

  // 2. Fallback a intentar cargar localmente competitions.json del paquete de la extensión
  try {
    const res = await fetch(chrome.runtime.getURL("competitions.json"));
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) return data;
    }
  } catch (e) {
    console.warn("No se pudo cargar competitions.json vía extension URL:", e);
  }

  // 3. Fallback estático con las competiciones activas principales de Sherlock
  return [
    { name: "2. Bundesliga", id: 44, season: 97406, active: true },
    { name: "Allsvenskan", id: 40, season: 87925, active: true },
    { name: "Austrian Bundesliga", id: 45, season: 97043, active: true },
    { name: "Brasileirão Betano", id: 325, season: 87678, active: true },
    { name: "Brasileirão Série B", id: 390, season: 89840, active: true },
    { name: "Canadian Premier League", id: 13470, season: 89676, active: true },
    { name: "Chinese Super League", id: 649, season: 90049, active: true },
    { name: "CONMEBOL Libertadores", id: 384, season: 87760, active: true },
    { name: "CONMEBOL Sudamericana", id: 480, season: 87770, active: true },
    { name: "Coppa Italia", id: 328, season: 97028, active: true },
    { name: "Czech First League", id: 172, season: 96966, active: true },
    { name: "División Profesional", id: 16736, season: 92509, active: true },
    { name: "EFL Cup", id: 21, season: 96185, active: true },
    { name: "Ekstraklasa", id: 202, season: 96144, active: true },
    { name: "Eliteserien", id: 20, season: 87809, active: true },
    { name: "HNL", id: 170, season: 95727, active: true },
    { name: "K League 1", id: 410, season: 88606, active: true },
    { name: "LaLiga", id: 8, season: 97268, active: true },
    { name: "LaLiga 2", id: 54, season: 97280, active: true },
    { name: "League One", id: 24, season: 97077, active: true },
    { name: "League Two", id: 25, season: 97078, active: true },
    { name: "Liga 1 Te Apuesto", id: 406, season: 88529, active: true },
    { name: "Liga de Primera", id: 11653, season: 88493, active: true },
    { name: "Liga MX, Apertura", id: 11621, season: 96191, active: true },
    { name: "Liga Portugal Betclic", id: 238, season: 97436, active: true },
    { name: "Liga Profesional de Fútbol", id: 155, season: 87913, active: true },
    { name: "LigaPro Serie A", id: 240, season: 89674, active: true },
    { name: "Ligue 1", id: 34, season: 96127, active: true },
    { name: "MLS", id: 242, season: 86668, active: true },
    { name: "Premier League", id: 17, "season": 96668, active: true },
    { name: "Primera A", id: 11539, season: 88503, active: true },
    { name: "Pro League", id: 28, season: 96616, active: true },
    { name: "Saudi Pro League", id: 955, season: 99275, active: true },
    { name: "Scottish Premiership", id: 36, season: 96658, active: true },
    { name: "Serie A", id: 23, season: 95836, active: true },
    { name: "VriendenLoterij Eredivisie", id: 37, season: 96143, active: true }
  ];
}

async function handleBulkExtractStatsUI() {
  if (!sherlockEndpoint) {
    showStatus("error", "Configura el endpoint de Sherlock en Settings");
    chrome.runtime.openOptionsPage();
    return;
  }
  const comps = await getActiveCompetitions();
  if (!comps || comps.length === 0) {
    showStatus("error", "No se pudieron cargar las competiciones activas");
    return;
  }

  const btnBulkStats = document.getElementById("btnBulkExtractStatsNoMatch");
  const btnCancelBulk = document.getElementById("btnCancelBulkExtract");

  if (btnBulkStats) btnBulkStats.style.display = "none";
  if (btnCancelBulk) {
    btnCancelBulk.style.display = "block";
    btnCancelBulk.onclick = async () => {
      showStatus("loading", "⏳ Cancelando extracción...");
      await chrome.runtime.sendMessage({ action: "cancelBulkExtraction" });
    };
  }

  showStatus("loading", "Iniciando extracción masiva de partidos...");
  showProgress(10);

  // Escuchar progreso bulk
  const listener = (msg) => {
    if (msg.action === "bulkProgress") {
      const d = msg.data;
      showStatus(d.phase === "error" ? "error" : "loading", d.message || "");
      if (d.total && d.done !== undefined) {
        showProgress(Math.min(100, Math.round((d.done / d.total) * 100)));
      }
    }
  };
  chrome.runtime.onMessage.addListener(listener);

  try {
    let baseUrl = sherlockEndpoint;
    if (baseUrl.includes("/api/v1")) baseUrl = baseUrl.split("/api/v1")[0];

    const res = await chrome.runtime.sendMessage({
      action: "bulkExtractStats",
      data: { baseUrl, competitions: comps },
    });

    showProgress(100);
    if (res && res.success) {
      showStatus(
        "success",
        `✅ ${res.totalSaved} partidos guardados, ${res.totalErrors} errores${
          res.recalcResult ? " — historial recalculado" : ""
        }`,
      );
    } else if (res && res.cancelled) {
      showStatus("error", "⏹ Extracción masiva cancelada por el usuario");
    } else {
      showStatus("error", `❌ ${res?.error || "Error en proceso"}`);
    }
  } catch (err) {
    showStatus("error", `❌ Error: ${err.message}`);
  } finally {
    if (btnBulkStats) btnBulkStats.style.display = "block";
    if (btnCancelBulk) btnCancelBulk.style.display = "none";
    chrome.runtime.onMessage.removeListener(listener);
    setTimeout(() => hideProgress(), 3000);
  }
}

async function handleBulkExtractResultsUI() {
  if (!sherlockEndpoint) {
    showStatus("error", "Configura el endpoint de Sherlock en Settings");
    chrome.runtime.openOptionsPage();
    return;
  }
  const comps = await getActiveCompetitions();
  if (!comps || comps.length === 0) {
    showStatus("error", "No se pudieron cargar las competiciones activas");
    return;
  }

  showStatus("loading", "Buscando resultados del día...");
  showProgress(10);

  const listener = (msg) => {
    if (msg.action === "bulkProgress") {
      const d = msg.data;
      showStatus(d.phase === "error" ? "error" : "loading", d.message || "");
      if (d.total && d.done !== undefined) {
        showProgress(Math.min(100, Math.round((d.done / d.total) * 100)));
      }
    }
  };
  chrome.runtime.onMessage.addListener(listener);

  try {
    let baseUrl = sherlockEndpoint;
    if (baseUrl.includes("/api/v1")) baseUrl = baseUrl.split("/api/v1")[0];

    const res = await chrome.runtime.sendMessage({
      action: "bulkExtractResults",
      data: { baseUrl, competitions: comps },
    });

    showProgress(100);
    if (res && res.success) {
      showStatus("success", `✅ Resultados: ${res.totalSaved} guardados, ${res.totalErrors} errores`);
    } else if (res && res.cancelled) {
      showStatus("error", "⏹ Extracción cancelada");
    } else {
      showStatus("error", `❌ ${res?.error || "Error en proceso"}`);
    }
  } catch (err) {
    showStatus("error", `❌ Error: ${err.message}`);
  } finally {
    chrome.runtime.onMessage.removeListener(listener);
    setTimeout(() => hideProgress(), 3000);
  }
}
// ═══════════════════════════════════════════════════════════════
// EXTRACCIÓN DE RESULTADOS FINALES
// ═══════════════════════════════════════════════════════════════
async function handleExtractResults() {
  if (!currentMatchData) {
    showStatus("error", "No hay datos de partido disponibles");
    return;
  }
  const { eventId } = currentMatchData;
  if (!eventId) {
    showStatus("error", "Falta ID del evento");
    return;
  }
  showStatus("loading", "Extrayendo resultados finales...");
  showProgress(20);
  try {
    const result = await chrome.runtime.sendMessage({
      action: "extractResults",
      data: { eventId, url: currentUrl },
    });
    showProgress(100);
    if (!result || !result.success) {
      throw new Error(result?.error || "Error en extracción de resultados");
    }
    showStatus(
      "success",
      `✅ Resultados enviados a Sherlock.\n${result.message || ""}`,
    );
  } catch (error) {
    showStatus("error", `❌ ${error.message}`);
    console.error("Error en extracción de resultados:", error);
  } finally {
    setTimeout(() => hideProgress(), 1500);
  }
}
async function handleSaveMatchWithoutStats() {
  if (!currentMatchData) {
    showStatus("error", "No hay datos de partido disponibles");
    return;
  }
  if (!sherlockEndpoint) {
    showStatus("error", "Configura el endpoint de Sherlock en Settings");
    chrome.runtime.openOptionsPage();
    return;
  }
  showStatus("loading", "Guardando partido (sin stats)...");
  showProgress(25);
  try {
    // build minimum payload with match data
    const payload = buildSherlockPayload({
      match: currentMatchData.event || currentMatchData,
    });
    payload.has_real_stats = false;
    // We send to `/api/v1/analysis/quick-save` endpoint
    let quickSaveUrl = sherlockEndpoint;
    if (quickSaveUrl.includes("/api/v1/prefill")) {
      quickSaveUrl = quickSaveUrl.replace(
        "/api/v1/prefill",
        "/api/v1/analysis/quick-save",
      );
    } else {
      quickSaveUrl = quickSaveUrl + "/analysis/quick-save";
    }
    showProgress(60);
    const response = await fetch(quickSaveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Source": "sofascore-extractor",
        "X-Extractor-Version": "1.1.0",
        "X-Event-Id": currentEventId || "unknown",
      },
      body: JSON.stringify(payload),
    });
    showProgress(100);
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Error ${response.status}: ${errorText}`);
    }
    const result = await response.json();
    showStatus(
      "success",
      `✅ Partido guardado: ${result.match_title || "Correctamente"}`,
    );
  } catch (error) {
    showStatus("error", `❌ Error: ${error.message}`);
    console.error("Error guardando partido:", error);
  } finally {
    setTimeout(() => hideProgress(), 1500);
  }
}

// ═══════════════════════════════════════════════════════════════
// EXTRACCIÓN DE ESTADÍSTICAS
// ═══════════════════════════════════════════════════════════════
async function handleExtract() {
  if (!currentMatchData) {
    showStatus("error", "No hay datos de partido disponibles");
    return;
  }
  const {
    eventId,
    homeTeamId,
    awayTeamId,
    tournamentId,
    uniqueTournamentId,
    seasonId,
  } = currentMatchData;
  if (
    !homeTeamId ||
    !awayTeamId ||
    !tournamentId ||
    !uniqueTournamentId ||
    !seasonId
  ) {
    showStatus("error", "Faltan IDs necesarios para la extracción");
    return;
  }
  showStatus("loading", "Extrayendo estadísticas...");
  showProgress(10);
  try {
    // Enviar mensaje al background script para extracción completa
    const result = await chrome.runtime.sendMessage({
      action: "extractStats",
      data: {
        eventId: eventId,
        url: currentUrl,
        homeTeamId: homeTeamId,
        awayTeamId: awayTeamId,
        tournamentId: tournamentId,
        uniqueTournamentId: uniqueTournamentId,
        seasonId: seasonId,
      },
    });
    showProgress(70);
    if (!result || !result.success) {
      throw new Error(result?.error || "Error en extracción");
    }
    extractedData = result.data;
    showProgress(100);
    showStatsPreview();
    showStatus("success", "✅ Estadísticas extraídas correctamente");
    // Auto-enviar si está configurado
    const settings = await chrome.storage.sync.get(["autoSend"]);
    if (settings.autoSend === "after_extract" && sherlockEndpoint) {
      setTimeout(() => handleSendToSherlock(), 500);
    }
  } catch (error) {
    showStatus("error", `❌ ${error.message}`);
    console.error("Error en extracción:", error);
  } finally {
    setTimeout(() => hideProgress(), 1500);
  }
}
// ═══════════════════════════════════════════════════════════════
// ENVÍO A SHERLOCK
// ═══════════════════════════════════════════════════════════════
function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function handleSendToSherlock() {
  if (!extractedData) {
    showStatus("error", "Primero extrae las estadísticas");
    return;
  }
  if (!sherlockEndpoint) {
    showStatus("error", "Configura el endpoint de Sherlock en Settings");
    chrome.runtime.openOptionsPage();
    return;
  }
  showStatus("loading", "Enviando a Sherlock...");
  showProgress(20);
  try {
    const payload = buildSherlockPayload(extractedData);
    showProgress(60);
    const response = await fetch(sherlockEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Source": "sofascore-extractor",
        "X-Extractor-Version": "1.1.0",
        "X-Event-Id": currentEventId || "unknown",
      },
      body: JSON.stringify(payload),
    });
    showProgress(100);
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Error ${response.status}: ${errorText}`);
    }
    const result = await response.json().catch(() => ({}));
    showStatus("success", `✅ Enviado a Sherlock. ${result.message || ""}`);

    // ── NUEVO: 1s después, mandar TODAS las cuotas exitosas en un solo POST ──
    const oddsByBookmaker = extractedData.oddsByBookmaker || {};
    const successfulEntries = Object.entries(oddsByBookmaker).filter(
      ([, res]) => res?.success,
    );

    if (successfulEntries.length > 0) {
      await delay(1000);

      const combinedPayload = {};
      successfulEntries.forEach(([bookmakerKey, res]) => {
        combinedPayload[bookmakerKey] = res.payload;
      });

      const base = sherlockEndpoint.replace(/\/+$/, "");
      const oddsUrl = base.includes("/api/v1/prefill")
        ? `${base}/odds`
        : `${base}/api/v1/prefill/odds`;

      try {
        const oddsResponse = await fetch(oddsUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ odds_by_bookmaker: combinedPayload }),
        });

        const bookmakerNames = successfulEntries.map(([k]) => k).join(", ");

        if (oddsResponse.ok) {
          showStatus(
            "success",
            `✅ Stats + cuotas enviadas (${bookmakerNames})`,
          );
        } else {
          console.error(
            "[Watson] Error enviando cuotas combinadas:",
            oddsResponse.status,
            oddsUrl,
          );
          showStatus(
            "error",
            `⚠️ Stats enviadas, pero las cuotas fallaron (HTTP ${oddsResponse.status})`,
          );
        }

        // Reflejar en caché
        successfulEntries.forEach(([, res]) => {
          res.sentToSherlock = oddsResponse.ok;
        });
        await chrome.storage.local.set({ lastExtractedStats: extractedData });
      } catch (oddsErr) {
        console.error(
          "[Watson] Excepción enviando cuotas combinadas:",
          oddsErr,
        );
        showStatus(
          "error",
          `⚠️ Stats enviadas, pero hubo un error con las cuotas: ${oddsErr.message}`,
        );
      }
    } else {
      const errores = Object.entries(oddsByBookmaker)
        .map(([bk, res]) => `${bk}: ${res?.error || "sin datos"}`)
        .join(" | ");
      if (errores) {
        console.warn(
          "[Watson] Ninguna casa de apuestas encontró cuotas:",
          errores,
        );
      }
    }
  } catch (error) {
    showStatus("error", `❌ Error: ${error.message}`);
    console.error("Error enviando a Sherlock:", error);
  } finally {
    setTimeout(() => hideProgress(), 2500);
  }
}

// ═══════════════════════════════════════════════════════════════
// VER JSON
// ═══════════════════════════════════════════════════════════════
function handleViewJson() {
  if (!extractedData) {
    showStatus("error", "No hay datos para mostrar");
    return;
  }
  let payload;
  try {
    payload = buildSherlockPayload(extractedData);
  } catch (e) {
    payload = { error: e.message, rawData: extractedData };
  }
  const jsonStr = JSON.stringify(payload, null, 2);
  const blob = new Blob([jsonStr], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  chrome.tabs.create({ url: url });
}
// ═══════════════════════════════════════════════════════════════
// INFO DEL PARTIDO (con fetch a API)
// ═══════════════════════════════════════════════════════════════
async function showMatchInfo(eventId, url) {
  els.matchContainer.style.display = "none";
  els.statsContainer.style.display = "block";
  try {
    // Consultar API principal del evento
    const eventData = await fetchSofaScoreAPI(`/api/v1/event/${eventId}`);
    if (eventData && eventData.event) {
      const event = eventData.event;
      currentMatchData = {
        eventId,
        event: event,
        url,
        homeTeamId: event.homeTeam?.id,
        awayTeamId: event.awayTeam?.id,
        tournamentId: event.tournament?.id,
        uniqueTournamentId: event.tournament?.uniqueTournament?.id,
        seasonId: event.season?.id,
        start_timestamp: event.startTimestamp,
      };
      // Mostrar equipos
      els.homeTeam.textContent =
        event.homeTeam?.shortName || event.homeTeam?.name || "Local";
      els.homeTeamId.textContent = `ID: ${event.homeTeam?.id || "-"}`;
      els.awayTeam.textContent =
        event.awayTeam?.shortName || event.awayTeam?.name || "Visitante";
      els.awayTeamId.textContent = `ID: ${event.awayTeam?.id || "-"}`;
      els.eventId.textContent = `Event ID: ${eventId}`;
      // Mostrar marcador actual si está disponible
      if (event.homeScore) {
        els.goalsScored.textContent = `${event.homeScore.normaltime || 0} - ${event.awayScore.normaltime || 0}`;
        els.goalsScoredTeam.textContent = "Marcador actual";
      }
    } else {
      // Fallback: extraer del título de la pestaña
      const [tab] = await chrome.tabs.query({
        active: true,
        currentWindow: true,
      });
      const title = tab.title || "";
      const teamsMatch = title.match(/(.+?)\s+vs\.?\s+(.+?)(?:\s+[-–]|$)/i);
      if (teamsMatch) {
        els.homeTeam.textContent = teamsMatch[1].trim();
        els.awayTeam.textContent = teamsMatch[2].trim();
      } else {
        els.homeTeam.textContent = "Local";
        els.awayTeam.textContent = "Visitante";
      }
      els.eventId.textContent = `Event ID: ${eventId}`;
    }
  } catch (error) {
    console.warn("Error cargando datos del evento:", error);
    // Fallback al título
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });
    const title = tab.title || "";
    const teamsMatch = title.match(/(.+?)\s+vs\.?\s+(.+?)(?:\s+[-–]|$)/i);
    if (teamsMatch) {
      els.homeTeam.textContent = teamsMatch[1].trim();
      els.awayTeam.textContent = teamsMatch[2].trim();
    }
    els.eventId.textContent = `Event ID: ${eventId}`;
  }
}
// ═══════════════════════════════════════════════════════════════
// MODO BETANO
// ═══════════════════════════════════════════════════════════════
async function showBetanoMode(url) {
  // Ocultar header normal, mostrar header naranja
  const mainHeader = document.getElementById("mainHeader");
  const betanoHeader = document.getElementById("betanoHeader");
  if (mainHeader) mainHeader.style.display = "none";
  if (betanoHeader) betanoHeader.style.display = "block";

  // Ocultar las otras vistas, mostrar la Betano
  const matchContainer = document.getElementById("matchContainer");
  const statsContainer = document.getElementById("statsContainer");
  const historicalContainer = document.getElementById("historicalContainer");
  const betanoContainer = document.getElementById("betanoContainer");
  if (matchContainer) matchContainer.style.display = "none";
  if (statsContainer) statsContainer.style.display = "none";
  if (historicalContainer) historicalContainer.style.display = "none";
  if (betanoContainer) betanoContainer.style.display = "block";

  // Mostrar endpoint
  const endpointEl = document.getElementById("betanoEndpointUrl");
  if (endpointEl) {
    if (sherlockEndpoint) {
      endpointEl.textContent = sherlockEndpoint;
      endpointEl.classList.remove("not-set");
    } else {
      endpointEl.textContent = "No configurado - Ve a Settings";
      endpointEl.classList.add("not-set");
    }
  }

  // Intenta extraer nombre del partido de la URL para mostrar algo inmediato
  const slugMatch = url.match(/\/cuotas-de-partido\/([^\/]+)/);
  if (slugMatch) {
    const matchEl = document.getElementById("betanoMatchName");
    if (matchEl) {
      // Slug ej: "mushuc-runa-orense" → "Mushuc Runa vs Orense" (aproximado)
      const readable = slugMatch[1]
        .replace(/-vs-/, " vs ")
        .replace(/-/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());
      matchEl.textContent = readable;
    }
  }

  // Botón de settings
  const btnSettings = document.getElementById("btnBetanoSettings");
  if (btnSettings) {
    btnSettings.addEventListener("click", () =>
      chrome.runtime.openOptionsPage(),
    );
  }

  // Cargar datos cacheados
  const cached = await chrome.storage.local.get(["lastBetanoOdds"]);
  const btnSend = document.getElementById("btnSendBetanoOdds");

  if (cached.lastBetanoOdds && cached.lastBetanoOdds.url === url) {
    const data = cached.lastBetanoOdds;
    betanoOddsPayload = data.payload;

    const matchEl = document.getElementById("betanoMatchName");
    const badgeEl = document.getElementById("betanoBadge");
    const hintEl = document.getElementById("betanoHint");

    if (matchEl && data.homeTeam) {
      matchEl.textContent = `${data.homeTeam} vs ${data.awayTeam}`;
    }
    if (badgeEl) {
      badgeEl.textContent = "Listo para enviar";
      badgeEl.className = "betano-badge scanning";
    }
    if (hintEl) {
      hintEl.textContent =
        "Cuotas cargadas en Watson. Presiona el botón para enviarlas a Sherlock.";
      hintEl.style.color = "#f59e0b";
    }
    if (btnSend) {
      btnSend.disabled = false;
    }
  }

  // Listener para envío manual
  if (btnSend) {
    btnSend.replaceWith(btnSend.cloneNode(true)); // Limpiar listeners previos
    const newBtnSend = document.getElementById("btnSendBetanoOdds");
    newBtnSend.addEventListener("click", async () => {
      if (!betanoOddsPayload) return;
      if (!sherlockEndpoint) {
        showBetanoStatus("error", "Configura el endpoint en Settings");
        return;
      }

      showBetanoStatus("loading", "Enviando cuotas...");
      newBtnSend.disabled = true;

      try {
        const base = sherlockEndpoint.replace(/\/+$/, "");
        const urlPrefill = `${base}/odds`;

        const response = await fetch(urlPrefill, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(betanoOddsPayload),
        });

        if (response.ok) {
          showBetanoStatus(
            "success",
            "✅ Cuotas enviadas a Sherlock correctamente",
          );
          const badgeEl = document.getElementById("betanoBadge");
          if (badgeEl) {
            badgeEl.textContent = "Enviado ✅";
            badgeEl.className = "betano-badge captured";
          }
          const hintEl = document.getElementById("betanoHint");
          if (hintEl) {
            hintEl.textContent =
              "Las cuotas fueron inyectadas en Sherlock. Abre el comparador.";
            hintEl.style.color = "#065f46";
          }
        } else {
          throw new Error(`HTTP ${response.status}`);
        }
      } catch (err) {
        showBetanoStatus("error", `❌ Error al enviar: ${err.message}`);
        newBtnSend.disabled = false;
      }
    });
  }
}

function showBetanoStatus(type, message) {
  const statusEl = document.getElementById("betanoStatus");
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.className = `status show ${type}`;
  if (type === "success" || type === "error") {
    setTimeout(() => {
      statusEl.classList.remove("show");
    }, 5000);
  }
}

// ═══════════════════════════════════════════════════════════════
// MOSTRAR VISTA "NO HAY PARTIDO"
// ═══════════════════════════════════════════════════════════════
function showNoMatch() {
  els.matchContainer.style.display = "block";
  els.statsContainer.style.display = "none";

  const btnBulkStats = document.getElementById("btnBulkExtractStatsNoMatch");
  const btnBulkResults = document.getElementById("btnBulkExtractResultsNoMatch");
  const btnSettings = document.getElementById("btnNoMatchSettings");

  if (btnBulkStats) {
    btnBulkStats.onclick = handleBulkExtractStatsUI;
  }
  if (btnBulkResults) {
    btnBulkResults.onclick = handleBulkExtractResultsUI;
  }
  if (btnSettings) {
    btnSettings.onclick = () => chrome.runtime.openOptionsPage();
  }
}
// ═══════════════════════════════════════════════════════════════
// MOSTRAR PREVIEW DE ESTADÍSTICAS
// ═══════════════════════════════════════════════════════════════
function showStatsPreview() {
  if (!extractedData) return;
  const homeStats = extractedData.homeTeamStats?.statistics;
  const awayStats = extractedData.awayTeamStats?.statistics;
  if (homeStats && awayStats) {
    // Goles marcados en torneo
    els.goalsScored.textContent = `${homeStats.goalsScored ?? "-"} - ${awayStats.goalsScored ?? "-"}`;
    els.goalsScoredTeam.textContent = "Total en torneo";
    // Goles recibidos en torneo
    els.goalsConceded.textContent = `${homeStats.goalsConceded ?? "-"} - ${awayStats.goalsConceded ?? "-"}`;
    els.goalsConcededTeam.textContent = "Total en torneo";
    // Posesión
    els.avgPossession.textContent = `${homeStats.averageBallPossession?.toFixed(1) || 0}%`;
    els.avgPossessionTeam.textContent =
      extractedData.match?.homeTeam?.shortName ||
      extractedData.match?.homeTeam?.name ||
      "Local";
    // Tiros a puerta
    els.shotsOnTarget.textContent = `${homeStats.shotsOnTarget ?? "-"} - ${awayStats.shotsOnTarget ?? "-"}`;
    els.shotsOnTargetTeam.textContent = "Total en torneo";
  }
  // Habilitar botón de enviar
  els.btnSend.disabled = false;
  els.btnSend.style.opacity = "1";
}
// ═══════════════════════════════════════════════════════════════
// UI HELPERS
// ═══════════════════════════════════════════════════════════════
function updateEndpointDisplay() {
  if (sherlockEndpoint) {
    els.endpointUrl.textContent = sherlockEndpoint;
    els.endpointUrl.classList.remove("not-set");
  } else {
    els.endpointUrl.textContent = "No configurado - Ve a Settings";
    els.endpointUrl.classList.add("not-set");
  }
}
function showStatus(type, message) {
  if (els.status) {
    els.status.textContent = message;
    els.status.className = `status show ${type}`;
  }
  const noMatchStatus = document.getElementById("noMatchStatus");
  if (noMatchStatus) {
    noMatchStatus.textContent = message;
    noMatchStatus.className = `status show ${type}`;
  }
  if (type === "success" || type === "error") {
    setTimeout(() => {
      if (els.status) els.status.classList.remove("show");
      if (noMatchStatus) noMatchStatus.classList.remove("show");
    }, 5000);
  }
}
function showProgress(percent) {
  if (els.progressBar) {
    els.progressBar.classList.add("show");
    els.progressFill.style.width = `${percent}%`;
  }
  const noMatchProgressBar = document.getElementById("noMatchProgressBar");
  const noMatchProgressFill = document.getElementById("noMatchProgressFill");
  if (noMatchProgressBar && noMatchProgressFill) {
    noMatchProgressBar.classList.add("show");
    noMatchProgressFill.style.width = `${percent}%`;
  }
}
function hideProgress() {
  if (els.progressBar) {
    els.progressBar.classList.remove("show");
    els.progressFill.style.width = "0%";
  }
  const noMatchProgressBar = document.getElementById("noMatchProgressBar");
  const noMatchProgressFill = document.getElementById("noMatchProgressFill");
  if (noMatchProgressBar && noMatchProgressFill) {
    noMatchProgressBar.classList.remove("show");
    noMatchProgressFill.style.width = "0%";
  }
}
// ═══════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════
function extractEventIdFromUrl(url) {
  let match = url.match(/#id:(\d+)/);
  if (match) return match[1];
  match = url.match(/\/event\/(\d+)/);
  if (match) return match[1];
  match = url.match(/[?#&]id[=:](\d+)/);
  if (match) return match[1];
  return null;
}
async function fetchSofaScoreAPI(path) {
  const url = `https://www.sofascore.com${path}`;
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
      "X-Requested-With": "XMLHttpRequest",
    },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

// ═══════════════════════════════════════════════════════════════
// SECCIÓN HISTÓRICA — COMPETICIÓN
// ═══════════════════════════════════════════════════════════════

let _currentTournamentId = null;
let _currentTournamentName = null;
let _allMatchesCache = [];

/** Detecta el ID de torneo en URLs de competición de SofaScore.
 *  Ejemplos:
 *    /football/tournament/brazil/brasileirao-serie-b/390
 *    /football/tournament/brazil/brasileirao-serie-b/390#id:89840  ← #id es la temporada
 *  Devuelve el tournamentId (390) o null si no es URL de competición.
 */
function extractTournamentIdFromUrl(url) {
  // La clave: si la URL tiene /tournament/ en el path es una página de liga/copa
  const m = url.match(/\/tournament\/[^/]+\/[^/]+\/(\d+)/);
  return m ? m[1] : null;
}

/** Extrae el seasonId del hash #id:XXXX en URLs de competición (opcional). */
function extractSeasonIdFromTournamentUrl(url) {
  const m = url.match(/#id:(\d+)/);
  return m ? m[1] : null;
}

/** Inicializa la sección histórica cuando se detecta una competición */
async function initHistoricalSection(tournamentId, url) {
  _currentTournamentId = tournamentId;

  // Ocultar UI de partido, mostrar UI de competición
  els.matchContainer.style.display = "none";
  els.statsContainer.style.display = "none";
  els.historicalContainer.style.display = "block";

  // Mostrar endpoint
  if (sherlockEndpoint) {
    els.historicalEndpointUrl.textContent = sherlockEndpoint;
    els.historicalEndpointUrl.classList.remove("not-set");
  }

  // Intentar obtener nombre de la competición
  try {
    const info = await fetchSofaScoreAPI(
      `/api/v1/unique-tournament/${tournamentId}`,
    );
    _currentTournamentName =
      info?.uniqueTournament?.name || info?.tournament?.name || "Competición";
    els.competitionName.textContent = _currentTournamentName;
  } catch (e) {
    _currentTournamentName = "Competición";
    els.competitionName.textContent = "Competición";
  }
  els.competitionId.textContent = `Tournament ID: ${tournamentId}`;

  // Cargar lista de temporadas en el dropdown
  try {
    const seasonsData = await fetchSofaScoreAPI(
      `/api/v1/unique-tournament/${tournamentId}/seasons`,
    );
    if (seasonsData && seasonsData.seasons && els.seasonSelect) {
      els.seasonSelect.innerHTML = `<option value="all">🌐 Todas las temporadas (${seasonsData.seasons.length})</option>`;
      seasonsData.seasons.forEach((s) => {
        const opt = document.createElement("option");
        opt.value = String(s.id);
        opt.textContent = `📅 Temporada ${s.year} (ID: ${s.id})`;
        els.seasonSelect.appendChild(opt);
      });
    }
  } catch (err) {
    console.warn("No se pudieron cargar las temporadas para el dropdown", err);
  }

  // Cargar partidos ya guardados en storage
  const storageKey = `tournament_${tournamentId}_events`;
  const stored = await chrome.storage.local.get([storageKey]);
  if (stored[storageKey] && stored[storageKey].length > 0) {
    _allMatchesCache = stored[storageKey];
    showMatchesSection(_allMatchesCache);
  }

  // Listener de progreso desde background
  chrome.runtime.onMessage.addListener(onHistoricalProgress);
}

function setupHistoricalEventListeners() {
  els.btnExtractHistorical.addEventListener("click", handleExtractHistorical);
  els.btnCancelHistorical.addEventListener("click", handleCancelHistorical);
  els.btnSettings.addEventListener("click", () =>
    chrome.runtime.openOptionsPage(),
  );

  // Toggle lista de partidos
  els.matchesToggle.addEventListener("click", () => {
    const list = els.matchesList;
    const isOpen = list.classList.contains("open");
    list.classList.toggle("open", !isOpen);
    els.matchesSearch.style.display = isOpen ? "none" : "block";
    els.matchesToggle.textContent = isOpen ? "▼ Mostrar" : "▲ Ocultar";
  });

  // Búsqueda de equipos
  els.matchesSearch.addEventListener("input", () => {
    const q = els.matchesSearch.value.toLowerCase().trim();
    renderMatchesList(_allMatchesCache, q);
  });
}

async function handleExtractHistorical() {
  if (!sherlockEndpoint) {
    showHistoricalStatus(
      "error",
      "Configura el endpoint de Sherlock en Settings",
    );
    chrome.runtime.openOptionsPage();
    return;
  }

  els.btnExtractHistorical.disabled = true;
  els.btnCancelHistorical.disabled = false;
  els.historicalCounters.style.display = "flex";
  els.historicalProgressDetail.style.display = "block";
  els.historicalProgressBar.style.display = "block";
  els.historicalProgressFill.style.width = "2%";
  els.cntProcessed.textContent = "0";
  els.cntSaved.textContent = "0";
  els.cntErrors.textContent = "0";
  showHistoricalStatus("loading", "Iniciando extracción histórica...");

  let baseUrl = sherlockEndpoint;
  if (baseUrl.includes("/api/v1")) baseUrl = baseUrl.split("/api/v1")[0];

  try {
    const targetSeasonId = els.seasonSelect ? els.seasonSelect.value : "all";
    const forceReextract = document.getElementById("chkForceHistorical")?.checked || false;
    const result = await chrome.runtime.sendMessage({
      action: "extractHistoricalData",
      data: {
        tournamentId: _currentTournamentId,
        tournamentName: _currentTournamentName,
        targetSeasonId,
        baseUrl,
        force: forceReextract,
      },
    });

    if (result && result.success) {
      showHistoricalStatus(
        "success",
        `✅ Completado: ${result.totalSaved} guardados, ${result.totalErrors} errores`,
      );
    } else if (result && result.cancelled) {
      showHistoricalStatus("error", "⏹ Cancelado por el usuario");
    } else {
      showHistoricalStatus(
        "error",
        `❌ ${result?.error || "Error desconocido"}`,
      );
    }
  } catch (e) {
    showHistoricalStatus("error", `❌ ${e.message}`);
  } finally {
    els.btnExtractHistorical.disabled = false;
    els.btnCancelHistorical.disabled = true;
    els.historicalProgressFill.style.width = "100%";
  }
}

async function handleCancelHistorical() {
  els.btnCancelHistorical.disabled = true;
  showHistoricalStatus("loading", "⏳ Cancelando...");
  await chrome.runtime.sendMessage({ action: "cancelHistoricalExtraction" });
}

/** Recibe mensajes de progreso desde el background */
function onHistoricalProgress(msg) {
  if (msg.action !== "historicalProgress") return;
  const d = msg.data;

  // Fase
  const phases = {
    seasons: "Obteniendo temporadas",
    season_start: "Procesando temporada",
    season_skipped: "⏭ Temporada omitida",
    fetching_events: "Descargando partidos",
    processing_event: "Guardando partido",
    season_saved: "✅ Temporada guardada",
    done: "Completado",
    cancelled: "Cancelado",
  };
  els.progressPhase.textContent = phases[d.phase] || d.phase || "";
  els.progressMessage.textContent = d.message || "";

  // Contadores
  if (d.totalProcessed !== undefined)
    els.cntProcessed.textContent = d.totalProcessed;
  if (d.totalSaved !== undefined) els.cntSaved.textContent = d.totalSaved;
  if (d.totalErrors !== undefined) els.cntErrors.textContent = d.totalErrors;

  // Barra de progreso basada en temporadas
  if (d.totalSeasons && d.seasonIndex !== undefined) {
    const pct = Math.min(((d.seasonIndex + 1) / d.totalSeasons) * 100, 98);
    els.historicalProgressFill.style.width = pct + "%";
  }

  // Actualizar lista de partidos al terminar cada temporada (season_saved o done)
  if ((d.phase === "season_saved" || d.phase === "done") && d.allEvents) {
    _allMatchesCache = d.allEvents;
    showMatchesSection(d.allEvents);
  }
}

/** Muestra la sección de partidos y renderiza la lista */
function showMatchesSection(events) {
  if (!events || events.length === 0) return;
  els.matchesSection.style.display = "block";
  els.matchesCount.textContent = events.length;
  renderMatchesList(events, "");
}

/** Renderiza la lista de partidos filtrada, ordenada por start_timestamp desc */
function renderMatchesList(events, filter) {
  const q = (filter || "").toLowerCase();
  let filtered = events;
  if (q) {
    filtered = events.filter(
      (e) =>
        (e.homeTeam?.shortName || e.homeTeam?.name || "")
          .toLowerCase()
          .includes(q) ||
        (e.awayTeam?.shortName || e.awayTeam?.name || "")
          .toLowerCase()
          .includes(q),
    );
  }

  // Ordenar por fecha descendente (más reciente primero)
  filtered = [...filtered].sort(
    (a, b) => (b.start_timestamp || 0) - (a.start_timestamp || 0),
  );

  if (filtered.length === 0) {
    els.matchesList.innerHTML = `<div class="matches-empty">${q ? 'Sin resultados para "' + q + '"' : "No hay partidos"}</div>`;
    return;
  }

  const rows = filtered.map((e) => {
    const date = e.start_timestamp ? formatTimestamp(e.start_timestamp) : "?";
    const home = e.homeTeam?.shortName || e.homeTeam?.name || "Local";
    const away = e.awayTeam?.shortName || e.awayTeam?.name || "Visitante";
    const hs = e.homeScore?.normaltime ?? "?";
    const as = e.awayScore?.normaltime ?? "?";
    const season = e._seasonYear || "";
    return `
      <div class="match-row">
        <span class="match-date">${date}</span>
        ${season ? `<span class="match-season">${season}</span>` : ""}
        <span class="match-teams">${home} vs ${away}</span>
        <span class="match-score">${hs}-${as}</span>
      </div>`;
  });

  els.matchesList.innerHTML = rows.join("");
}

/** Formatea un Unix timestamp a fecha legible (DD/MM/YY) */
function formatTimestamp(ts) {
  const d = new Date(ts * 1000);
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const year = String(d.getFullYear()).slice(-2);
  return `${day}/${month}/${year}`;
}

function showHistoricalStatus(type, message) {
  els.historicalStatus.textContent = message;
  els.historicalStatus.className = `status show ${type}`;
  if (type === "success" || type === "error") {
    setTimeout(() => els.historicalStatus.classList.remove("show"), 6000);
  }
}
