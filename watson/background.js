// background.js - Service Worker de Watson (SofaScore Extractor)
// Versión corregida con standings reales

// ═══════════════════════════════════════════════════════════════
// INSTALACIÓN
// ═══════════════════════════════════════════════════════════════
chrome.runtime.onInstalled.addListener((details) => {
    if (details.reason === 'install') {
        chrome.storage.sync.set({
            endpointUrl: 'http://localhost:8000/api/v1/prefill',
            authToken: '',
            extractLineups: true,
            extractStreaks: true,
            extractHomeStats: true,
            extractAwayStats: true,
            extractIncidents: false,
            extractHeatmaps: false,
            autoSend: 'never'
        });
        chrome.runtime.openOptionsPage();
    }
});

// ═══════════════════════════════════════════════════════════════
// MENSAJES
// ═══════════════════════════════════════════════════════════════
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'extractStats') {
        handleExtractStats(request.data).then(sendResponse).catch(err => {
            sendResponse({ success: false, error: err.message });
        });
        return true;
    }

    if (request.action === 'sendToEndpoint') {
        handleSendToEndpoint(request.data).then(sendResponse).catch(err => {
            sendResponse({ success: false, error: err.message });
        });
        return true;
    }

    if (request.action === 'extractResults') {
        handleExtractResults(request.data).then(sendResponse).catch(err => {
            sendResponse({ success: false, error: err.message });
        });
        return true;
    }
});

// ═══════════════════════════════════════════════════════════════
// EXTRACCIÓN DE RESULTADOS
// ═══════════════════════════════════════════════════════════════
async function handleExtractResults(data) {
    try {
        const { eventId } = data;
        const settings = await chrome.storage.sync.get(['endpointUrl']);
        if (!settings.endpointUrl) {
            throw new Error("Endpoint no configurado");
        }
        
        let baseUrl = settings.endpointUrl;
        if (baseUrl.includes("/api/v1")) {
            baseUrl = baseUrl.split("/api/v1")[0];
        }

        // 1. Fetch Event Info
        const eventData = await fetchSofaScore(`/api/v1/event/${eventId}`);
        if (!eventData || !eventData.event) throw new Error("No se pudo obtener el evento");
        
        // 2. Fetch Statistics
        let statisticsData = null;
        try {
            statisticsData = await fetchSofaScore(`/api/v1/event/${eventId}/statistics`);
        } catch(e) { console.warn("No statistics", e.message); }

        // 3. Fetch Incidents
        let incidentsData = null;
        try {
            incidentsData = await fetchSofaScore(`/api/v1/event/${eventId}/incidents`);
        } catch(e) { console.warn("No incidents", e.message); }
        
        // 4. Parse results
        const payload = {
            final_score_home: eventData.event.homeScore?.current || 0,
            final_score_away: eventData.event.awayScore?.current || 0
        };
        
        if (statisticsData && statisticsData.statistics) {
            const allPeriod = statisticsData.statistics.find(s => s.period === "ALL") || statisticsData.statistics[0];
            if (allPeriod) {
                allPeriod.groups.forEach(group => {
                    group.statisticsItems.forEach(item => {
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
        }
        
        if (incidentsData && incidentsData.incidents) {
            let rcHome = 0;
            let rcAway = 0;
            incidentsData.incidents.forEach(inc => {
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
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sport: 'football',
                home_team: eventData.event.homeTeam.name,
                away_team: eventData.event.awayTeam.name,
                ...payload
            })
        });
        
        if (!resPush.ok) {
            throw new Error(`Error en el servidor al enviar: ${resPush.status}`);
        }
        
        const resData = await resPush.json();
        
        return { success: true, message: resData.message || "Resultados enviados correctamente" };

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
            'extractLineups', 'extractStreaks', 'extractHomeStats',
            'extractAwayStats', 'extractIncidents', 'extractHeatmaps'
        ]);

        const result = {
            metadata: {
                extractedAt: new Date().toISOString(),
                source: 'sofascore.com',
                eventId,
                url: data.url
            },
            match: null,
            lineups: null,
            teamStreaks: null,
            incidents: null,
            homeTeamStats: null,
            awayTeamStats: null,
            standings: null  // ← NUEVO: standings del torneo
        };

        // 1. Info del evento
        const eventData = await fetchSofaScore(`/api/v1/event/${eventId}`);
        result.match = eventData.event;

        // 2. STANDINGS (para wins/draws/losses reales)
        if (tournamentId && seasonId) {
            try {
                result.standings = await fetchSofaScore(
                    `/api/v1/tournament/${tournamentId}/season/${seasonId}/standings/total`
                );
            } catch (e) {
                console.warn('Standings:', e.message);
            }
        }

        // 3. Alineaciones
        if (settings.extractLineups) {
            try {
                result.lineups = await fetchSofaScore(`/api/v1/event/${eventId}/lineups`);
            } catch (e) { console.warn('Lineups:', e.message); }
        }

        // 4. Streaks
        if (settings.extractStreaks) {
            try {
                result.teamStreaks = await fetchSofaScore(`/api/v1/event/${eventId}/team-streaks`);
            } catch (e) { console.warn('Streaks:', e.message); }
        }

        // 5. Incidentes
        if (settings.extractIncidents) {
            try {
                result.incidents = await fetchSofaScore(`/api/v1/event/${eventId}/incidents`);
            } catch (e) { console.warn('Incidents:', e.message); }
        }

        // 6. Stats equipo local
        if (settings.extractHomeStats && homeTeamId && tournamentId && seasonId) {
            try {
                result.homeTeamStats = await fetchSofaScore(
                    `/api/v1/team/${homeTeamId}/unique-tournament/${tournamentId}/season/${seasonId}/statistics/overall`
                );
            } catch (e) { console.warn('Home stats:', e.message); }
        }

        // 7. Stats equipo visitante
        if (settings.extractAwayStats && awayTeamId && tournamentId && seasonId) {
            try {
                result.awayTeamStats = await fetchSofaScore(
                    `/api/v1/team/${awayTeamId}/unique-tournament/${tournamentId}/season/${seasonId}/statistics/overall`
                );
            } catch (e) { console.warn('Away stats:', e.message); }
        }

        // Guardar resultado
        await chrome.storage.local.set({
            lastExtractedStats: result,
            lastExtractedAt: Date.now()
        });

        // Auto-send
        const autoSend = (await chrome.storage.sync.get(['autoSend'])).autoSend;
        if (autoSend === 'after_extract') {
            await handleSendToEndpoint(result);
        }

        return { success: true, data: result };

    } catch (error) {
        console.error('Error en extracción:', error);
        return { success: false, error: error.message };
    }
}

// ═══════════════════════════════════════════════════════════════
// ENVÍO AL ENDPOINT
// ═══════════════════════════════════════════════════════════════
async function handleSendToEndpoint(data) {
    const settings = await chrome.storage.sync.get(['endpointUrl', 'authToken']);

    if (!settings.endpointUrl) {
        return { success: false, error: 'Endpoint no configurado' };
    }

    let payload;
    try {
        payload = buildSherlockPayload(data);
    } catch (error) {
        return { success: false, error: `Error mapeando datos: ${error.message}` };
    }

    const headers = {
        'Content-Type': 'application/json',
        'X-Source': 'sofascore-extractor',
        'X-Extractor-Version': '1.1.0',
        'X-Event-Id': data.metadata?.eventId || 'unknown'
    };

    if (settings.authToken) {
        headers['Authorization'] = settings.authToken.startsWith('Bearer') || settings.authToken.startsWith('Basic')
            ? settings.authToken
            : `Bearer ${settings.authToken}`;
    }

    try {
        const response = await fetch(settings.endpointUrl, {
            method: 'POST',
            headers,
            body: JSON.stringify(payload)
        });

        return {
            success: response.ok,
            status: response.status,
            statusText: response.statusText
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
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status} en ${path}`);
    }

    return await response.json();
}

// ═══════════════════════════════════════════════════════════════
// AUTO-DETECT EN CAMBIO DE PESTAÑA
// ═══════════════════════════════════════════════════════════════
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
    if (changeInfo.url && changeInfo.url.includes('sofascore.com')) {
        const eventId = extractEventIdFromUrl(changeInfo.url);
        if (eventId) {
            const autoSend = (await chrome.storage.sync.get(['autoSend'])).autoSend;
            if (autoSend === 'on_detect') {
                setTimeout(async () => {
                    try {
                        chrome.scripting.executeScript({
                            target: { tabId },
                            func: () => ({
                                url: window.location.href,
                                title: document.title
                            })
                        }, async (results) => {
                            if (results && results[0]) {
                                console.log('Página SofaScore detectada:', results[0].result);
                            }
                        });
                    } catch (e) {
                        console.warn('Auto-detect error:', e);
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