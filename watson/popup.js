// popup.js - Popup de Watson (SofaScore Extractor) con integración Sherlock
// ═══════════════════════════════════════════════════════════════
// ESTADO GLOBAL
// ═══════════════════════════════════════════════════════════════
let currentEventId = null;
let currentUrl = null;
let extractedData = null;
let sherlockEndpoint = "";
let currentMatchData = null;
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
    if (!tab.url || !tab.url.includes("sofascore.com")) {
      showNoMatch();
      return;
    }
    currentUrl = tab.url;
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
// ═══════════════════════════════════════════════════════════════
// EVENT LISTENERS
// ═══════════════════════════════════════════════════════════════
function setupEventListeners() {
  els.btnExtract.addEventListener("click", handleExtract);
  els.btnSend.addEventListener("click", handleSendToSherlock);
  if (els.btnExtractResults) {
    els.btnExtractResults.addEventListener("click", handleExtractResults);
  }
  els.btnViewJson.addEventListener("click", handleViewJson);
  els.btnSettings.addEventListener("click", () =>
    chrome.runtime.openOptionsPage(),
  );
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
// ═══════════════════════════════════════════════════════════════
// EXTRACCIÓN DE ESTADÍSTICAS
// ═══════════════════════════════════════════════════════════════
async function handleExtract() {
  if (!currentMatchData) {
    showStatus("error", "No hay datos de partido disponibles");
    return;
  }
  const { eventId, homeTeamId, awayTeamId, tournamentId, seasonId } =
    currentMatchData;
  if (!homeTeamId || !awayTeamId || !tournamentId || !seasonId) {
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
    // El background ya tiene el mapeador, pero construimos payload aquí también
    // para poder mostrarlo en View JSON
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
  } catch (error) {
    showStatus("error", `❌ Error: ${error.message}`);
    console.error("Error enviando a Sherlock:", error);
  } finally {
    setTimeout(() => hideProgress(), 1500);
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
        tournamentId: event.tournament?.uniqueTournament?.id,
        seasonId: event.season?.id,
        timestamp: new Date().toISOString(),
      };
      // Mostrar equipos
      els.homeTeam.textContent = event.homeTeam?.name || "Local";
      els.homeTeamId.textContent = `ID: ${event.homeTeam?.id || "-"}`;
      els.awayTeam.textContent = event.awayTeam?.name || "Visitante";
      els.awayTeamId.textContent = `ID: ${event.awayTeam?.id || "-"}`;
      els.eventId.textContent = `Event ID: ${eventId}`;
      // Mostrar marcador actual si está disponible
      if (event.homeScore) {
        els.goalsScored.textContent = `${event.homeScore.current || 0} - ${event.awayScore.current || 0}`;
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
// MOSTRAR VISTA "NO HAY PARTIDO"
// ═══════════════════════════════════════════════════════════════
function showNoMatch() {
  els.matchContainer.style.display = "block";
  els.statsContainer.style.display = "none";
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
      extractedData.match?.homeTeam?.name || "Local";
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
  els.status.textContent = message;
  els.status.className = `status show ${type}`;
  if (type === "success" || type === "error") {
    setTimeout(() => {
      els.status.classList.remove("show");
    }, 5000);
  }
}
function showProgress(percent) {
  els.progressBar.classList.add("show");
  els.progressFill.style.width = `${percent}%`;
}
function hideProgress() {
  els.progressBar.classList.remove("show");
  els.progressFill.style.width = "0%";
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
