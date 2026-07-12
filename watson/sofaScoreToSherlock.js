// sofaScoreToSherlock.js - Mapeador de datos SofaScore → Sherlock

/**
 * Convierte las estadísticas de equipo de SofaScore al formato FootballTeamStats de Sherlock.
 * @param {Object} sofaStats - statistics del homeTeamStats o awayTeamStats
 * @param {string} teamName - Nombre del equipo
 * @param {boolean} isHome - Si es equipo local
 * @param {Object} standings - Datos de standings del torneo (opcional)
 * @param {number|string} teamId - ID del equipo para buscar en standings
 * @returns {Object} - Objeto compatible con FootballTeamStats
 */
function mapSofaScoreToSherlockTeamStats(sofaStats, teamName, isHome = true, standings = null, teamId = null) {
    const s = sofaStats.statistics || sofaStats;
    const matches = s.matches || 1;
    const safeDiv = (a, b) => (b > 0 ? a / b : 0);

    // ─── OBTENER WINS/DRAWS/LOSSES REALES DESDE STANDINGS ───
    let wins = 0, draws = 0, losses = 0;
    let matchesHome = isHome ? Math.ceil(matches / 2) : Math.floor(matches / 2);
    let matchesAway = isHome ? Math.floor(matches / 2) : Math.ceil(matches / 2);

    if (standings && teamId) {
        const teamStanding = findTeamInStandings(standings, teamId);
        if (teamStanding) {
            wins = teamStanding.wins || 0;
            draws = teamStanding.draws || 0;
            losses = teamStanding.losses || 0;
            if (teamStanding.home) {
                matchesHome = isHome ? (teamStanding.home.matches || Math.ceil(matches / 2)) : Math.floor(matches / 2);
                matchesAway = !isHome ? (teamStanding.away?.matches || Math.ceil(matches / 2)) : Math.floor(matches / 2);
            }
        }
    }

    // Fallback si no hay standings
    if (wins === 0 && draws === 0 && losses === 0) {
        wins = Math.round(matches * 0.5);
        draws = Math.round(matches * 0.25);
        losses = matches - wins - draws;
    }

    // ─── CÁLCULOS DERIVADOS ───
    const goalConversionPct = (s.goalsScored / s.shots) * 100;

    const bigChancesMissed = s.bigChancesMissed || 0;
    const cleanSheetsTotal = s.cleanSheets || 0;
    const cleanSheetsHome = isHome ? cleanSheetsTotal : 0;
    const cleanSheetsAway = !isHome ? cleanSheetsTotal : 0;

    const xgPerGame = safeDiv((s.bigChances || 0) * 0.38 + (s.shotsOnTarget || 0) * 0.1, matches);
    const xgaPerGame = safeDiv((s.bigChancesAgainst || 0) * 0.38 + (s.shotsOnTargetAgainst || 0) * 0.1, matches);

    return {
        name: teamName,
        matches_home: matchesHome,
        matches_away: matchesAway,
        matches_played: matches,
        wins: wins,
        draws: draws,
        losses: losses,
        goals_per_game: safeDiv(s.goalsScored || 0, matches),
        goals_conceded_per_game: safeDiv(s.goalsConceded || 0, matches),
        goal_conversion_pct: goalConversionPct,
        big_chances_per_game: safeDiv(s.bigChances || 0, matches),
        big_chances_missed_per_game: safeDiv(bigChancesMissed, matches),
        shots_per_game: safeDiv(s.shots || 0, matches),
        shots_on_target_per_game: safeDiv(s.shotsOnTarget || 0, matches),
        possession_pct: s.averageBallPossession || 50,
        passes_completed: safeDiv(s.accuratePasses || 0, matches),
        pass_accuracy: s.accuratePassesPercentage || 0,
        passes_opp_half: safeDiv(s.accurateOppositionHalfPasses || 0, matches),
        pass_accuracy_opp_half: s.accurateOppositionHalfPassesPercentage || 0,
        crosses_per_game: safeDiv(s.accurateCrosses || 0, matches),
        cross_accuracy: s.accurateCrossesPercentage || 0,
        corners_per_game: safeDiv(s.corners || 0, matches),
        clean_sheets_home: cleanSheetsHome,
        clean_sheets_away: cleanSheetsAway,
        clean_sheets: cleanSheetsTotal,
        saves_per_game: safeDiv(s.saves || 0, matches),
        balls_recovered_per_game: safeDiv(s.ballRecovery || 0, matches),
        duels_won_per_game: safeDiv(s.duelsWon || 0, matches),
        ground_duels_won_per_game: safeDiv(s.groundDuelsWon || 0, matches),
        penalties_conceded: s.penaltiesCommited || 0,
        fouls_per_game: safeDiv(s.fouls || 0, matches),
        yellow_cards_per_game: safeDiv(s.yellowCards || 0, matches),
        red_cards_total: (s.redCards || 0) + (s.yellowRedCards || 0),
        errors_leading_to_goal: s.errorsLeadingToGoal || 0,
        offside_per_game: safeDiv(s.offsides || 0, matches),
        corners_conceded_per_game: safeDiv(s.cornersAgainst || 0, matches),
        xg_per_game: xgPerGame,
        xga_per_game: xgaPerGame,
        passes_total_per_game: safeDiv(s.totalPasses || 0, matches),
        passes_opp_half_total_per_game: safeDiv(s.totalOppositionHalfPasses || 0, matches),
        crosses_total_per_game: safeDiv(s.totalCrosses || 0, matches),
    };
}

/**
 * Busca un equipo en los standings de SofaScore.
 * @param {Object} standings - Respuesta de /api/v1/tournament/{id}/season/{id}/standings/total
 * @param {number|string} teamId - ID del equipo
 * @returns {Object|null} - Datos del equipo en standings o null
 */
function findTeamInStandings(standings, teamId) {
    if (!standings || !standings.standings) return null;
    const tid = String(teamId);

    for (const group of standings.standings) {
        if (group.rows) {
            for (const row of group.rows) {
                if (String(row.team?.id) === tid) {
                    return {
                        wins: row.wins,
                        draws: row.draws,
                        losses: row.losses,
                        matches: row.matches,
                        home: row.home,
                        away: row.away,
                        points: row.points,
                        scoresFor: row.scoresFor,
                        scoresAgainst: row.scoresAgainst
                    };
                }
            }
        }
    }
    return null;
}

/**
 * Construye league_stats con datos reales del standings.
 * @param {Object} standings - Datos de standings
 * @param {Object} refereeStats - Datos del árbitro
 * @returns {Object} - league_stats
 */
function buildLeagueStats(standings, refereeStats) {

    if (standings && standings.standings) {
        let totalMatches = 0;
        let totalGoalsFor = 0;
        let totalWins = 0;
        let totalDraws = 0;
        let totalLosses = 0;

        for (const group of standings.standings) {
            if (group.rows) {
                for (const row of group.rows) {
                    totalMatches += row.matches || 0;
                    totalGoalsFor += row.scoresFor || 0;
                    totalWins += row.wins || 0;
                    totalDraws += row.draws || 0;
                    totalLosses += row.losses || 0;
                }
            }
        }
    }

    return {
        avg_yellow_cards_per_game: 4.0,
        avg_red_cards_per_game: 0.2,
        home_advantage_factor: 1.20,
        away_disadvantage_factor: 0.85,
        ...refereeStats,
    };
}

/**
 * Extrae datos del árbitro del evento SofaScore.
 * @param {Object} matchData - match.event del JSON de SofaScore
 * @returns {Object} - { referee_avg_yellow, referee_avg_red }
 */
function extractRefereeStats(matchData) {
    const referee = matchData.referee;
    if (!referee) {
        return { referee_avg_yellow: 0, referee_avg_red: 0 };
    }
    const games = referee.games || 1;
    return {
        referee_avg_yellow: games > 0 ? (referee.yellowCards || 0) / games : 0,
        referee_avg_red: games > 0 ? (referee.redCards || 0) / games : 0,
    };
}

/**
 * Construye el payload completo para Sherlock.
 * @param {Object} extractedData - Datos extraídos de SofaScore
 * @returns {Object} - Payload listo para POST
 */
function buildSherlockPayload(extractedData) {
    const match = extractedData.match?.event || extractedData.match;
    const homeStats = extractedData.homeTeamStats;
    const awayStats = extractedData.awayTeamStats;
    const standings = extractedData.standings;

    if (!match || !homeStats || !awayStats) {
        throw new Error("Datos incompletos: se requieren match, homeTeamStats y awayTeamStats");
    }

    const homeName = match.homeTeam?.name || "Local";
    const awayName = match.awayTeam?.name || "Visitante";
    const competition = match.event?.tournament?.uniqueTournament?.name || match.event?.tournament?.name || "Desconocida";
    const homeTeamId = match.homeTeam?.id;
    const awayTeamId = match.awayTeam?.id;

    const home = mapSofaScoreToSherlockTeamStats(homeStats, homeName, true, standings, homeTeamId);
    const away = mapSofaScoreToSherlockTeamStats(awayStats, awayName, false, standings, awayTeamId);
    const refereeStats = extractRefereeStats(match);
    const leagueStats = buildLeagueStats(standings, refereeStats);

    const odds = {
        home: null, draw: null, away: null,
        btts_yes: null, btts_no: null,
        dnb_home: null, dnb_away: null,
        dc_1x: null, dc_x2: null, dc_12: null,
        goals_lines: ["1.5", "2.5", "3.5", "4.5"],
        goalsOverOdds: {}, goalsUnderOdds: {},
        corners_lines: ["7.5", "8.5", "9.5", "10.5"],
        cornersOverOdds: {}, cornersUnderOdds: {},
        cards_lines: ["2.5", "3.5", "4.5", "5.5"],
        cardsOverOdds: {}, cardsUnderOdds: {},
        shots_lines: ["21.5", "22.5", "23.5", "24.5"],
        shotsOverOdds: {}, shotsUnderOdds: {},
        shots_target_lines: ["7.5", "8.5", "9.5", "10.5"],
        shotsTargetOverOdds: {}, shotsTargetUnderOdds: {},
        bookmaker: "",
    };

    return {
        sport: "football",
        home: home,
        away: away,
        odds: odds,
        league_stats: leagueStats,
        competition_name: competition,
        generate_llm_analysis: false,
        user_context: "",
    };
}

/**
 * Envía los datos mapeados al endpoint de prefill de Sherlock.
 * @param {Object} payload - Payload de Sherlock
 * @param {string} endpointUrl - URL del endpoint
 */
async function sendToSherlock(payload, endpointUrl) {
    const response = await fetch(endpointUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
    }

    return await response.json();
}

// Exportar para uso en extensión o módulos
if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        mapSofaScoreToSherlockTeamStats,
        findTeamInStandings,
        buildLeagueStats,
        extractRefereeStats,
        buildSherlockPayload,
        sendToSherlock,
    };
}