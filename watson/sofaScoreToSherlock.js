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
function mapSofaScoreToSherlockTeamStats(
  sofaStats,
  teamName,
  isHome = true,
  standings = null,
  teamId = null,
) {
  const s = sofaStats.statistics || sofaStats;
  // ── Issue #5: matches=0 se deja como 0; safeDiv nunca dividirá por 0 ──
  const matches = s.matches || 0;
  const safeDiv = (a, b) => (b > 0 ? a / b : 0);

  // ─── OBTENER WINS/DRAWS/LOSSES REALES DESDE STANDINGS ───
  // ── Issue #5: si no hay standings, dejar como null en lugar de inventar 50/25/25 ──
  let wins = null,
    draws = null,
    losses = null;
  let matchesHome = null;
  let matchesAway = null;

  if (standings && teamId) {
    const teamStanding = findTeamInStandings(standings, teamId);
    if (teamStanding) {
      wins = teamStanding.wins ?? 0;
      draws = teamStanding.draws ?? 0;
      losses = teamStanding.losses ?? 0;
      if (teamStanding.home) {
        matchesHome = isHome
          ? (teamStanding.home.matches ?? null)
          : null;
        matchesAway = !isHome
          ? (teamStanding.away?.matches ?? null)
          : null;
      }
    }
  }

  // Si los standings no aportaron datos, aproximar desde matches totales
  // pero NO inventar 50/25/25 — dejar wins/draws/losses en null si no hay datos
  if (wins === null && matches > 0) {
    // Usamos los goles para approximar si están disponibles
    const goalsFor = s.goalsScored || 0;
    const goalsAgainst = s.goalsConceded || 0;
    // No inventamos; simplemente dejamos en 0 (campos obligatorios en el modelo)
    wins = 0;
    draws = 0;
    losses = 0;
  } else if (wins === null) {
    wins = 0;
    draws = 0;
    losses = 0;
  }

  // Aproximar home/away si no vinieron de standings
  if (matchesHome === null) {
    matchesHome = matches > 0 ? (isHome ? Math.ceil(matches / 2) : Math.floor(matches / 2)) : 0;
  }
  if (matchesAway === null) {
    matchesAway = matches > 0 ? (isHome ? Math.floor(matches / 2) : Math.ceil(matches / 2)) : 0;
  }

  // ── Issue #7: Tomar clean sheets de standings (home / away) si están disponibles ──
  const cleanSheetsTotal = s.cleanSheets || 0;
  let cleanSheetsHome = null;
  let cleanSheetsAway = null;

  if (standings && teamId) {
    const teamStanding = findTeamInStandings(standings, teamId);
    if (teamStanding) {
      if (teamStanding.home?.cleanSheets != null) {
        cleanSheetsHome = teamStanding.home.cleanSheets;
      }
      if (teamStanding.away?.cleanSheets != null) {
        cleanSheetsAway = teamStanding.away.cleanSheets;
      }
    }
  }

  // Fallback si los standings no traen cleanSheets por localía:
  // distribuir proporcionalmente o dejar en 0 en lugar de asignarlas todas al lado actual
  if (cleanSheetsHome === null) {
    cleanSheetsHome = cleanSheetsTotal > 0 && matches > 0 && matchesHome > 0
      ? Math.round((cleanSheetsTotal * matchesHome) / matches)
      : (isHome ? cleanSheetsTotal : 0);
  }
  if (cleanSheetsAway === null) {
    cleanSheetsAway = Math.max(0, cleanSheetsTotal - cleanSheetsHome);
  }

  // ─── Issue #1: Usar xG real por partido si SofaScore lo proporciona (s.expectedGoals) ───
  let xgPerGame = 0;
  let hasRealXg = false;
  if (s.expectedGoals != null && s.expectedGoals > 0) {
    xgPerGame = safeDiv(s.expectedGoals, matches);
    hasRealXg = true;
  } else {
    // Fallback: fórmula aproximada cuando no hay xG oficial en la API
    const xgBase =
      (s.bigChances || 0) * 0.38 +
      (s.shotsOnTarget || 0) * 0.1 +
      (s.hitWoodwork || 0) * 0.15 +
      (s.fastBreakShots || 0) * 0.05 +
      (s.freeKickShots || 0) * 0.03;

    const creationQuality = safeDiv(s.bigChancesCreated || 0, s.shots || 1);
    const creationFactor = 1 + (creationQuality - 0.1) * 0.5;
    const passFactor =
      1 + ((s.accurateOppositionHalfPassesPercentage || 70) - 70) / 200;
    xgPerGame = safeDiv(xgBase * creationFactor * passFactor, matches);
  }

  let xgaPerGame = 0;
  if (s.expectedGoalsAgainst != null && s.expectedGoalsAgainst > 0) {
    xgaPerGame = safeDiv(s.expectedGoalsAgainst, matches);
  } else {
    const xgaBase =
      (s.bigChancesAgainst || 0) * 0.38 +
      (s.shotsOnTargetAgainst || 0) * 0.1 +
      (s.hitWoodworkAgainst || 0) * 0.15 +
      (s.errorsLeadingToGoal || 0) * 0.4;

    const saveRate = safeDiv(s.saves || 0, s.shotsOnTargetAgainst || 1);
    const defensiveFactor = 1 - (saveRate - 0.6) * 0.2;
    xgaPerGame = safeDiv(xgaBase * defensiveFactor, matches);
  }

  return {
    // ═══════════════════════════════════════════════════════════
    // ESTADÍSTICAS BÁSICAS
    // ═══════════════════════════════════════════════════════════
    name: teamName,
    matches_home: matchesHome,
    matches_away: matchesAway,
    matches_played: matches,
    wins: wins,
    draws: draws,
    losses: losses,

    // ═══════════════════════════════════════════════════════════
    // GOLES
    // ═══════════════════════════════════════════════════════════
    goals_scored: s.goalsScored || 0,
    goals_conceded: s.goalsConceded || 0,
    own_goals: s.ownGoals || 0,
    assists: s.assists || 0,
    goals_inside_box: s.goalsFromInsideTheBox || 0,
    goals_outside_box: s.goalsFromOutsideTheBox || 0,
    headed_goals: s.headedGoals || 0,
    left_foot_goals: s.leftFootGoals || 0,
    right_foot_goals: s.rightFootGoals || 0,
    free_kick_goals: s.freeKickGoals || 0,
    fast_break_goals: s.fastBreakGoals || 0,
    penalty_goals: s.penaltyGoals || 0,

    // ═══════════════════════════════════════════════════════════
    // GOLES POR PARTIDO
    // ═══════════════════════════════════════════════════════════
    goals_per_game: safeDiv(s.goalsScored || 0, matches),
    goals_conceded_per_game: safeDiv(s.goalsConceded || 0, matches),
    goal_conversion_pct: safeDiv(s.goalsScored || 0, s.shots || 1) * 100,

    // ═══════════════════════════════════════════════════════════
    // TIROS
    // ═══════════════════════════════════════════════════════════
    shots: s.shots || 0,
    shots_on_target: s.shotsOnTarget || 0,
    shots_off_target: s.shotsOffTarget || 0,
    shots_blocked: s.blockedScoringAttempt || 0,
    shots_inside_box: s.shotsFromInsideTheBox || 0,
    shots_outside_box: s.shotsFromOutsideTheBox || 0,
    big_chances: s.bigChances || 0,
    big_chances_created: s.bigChancesCreated || 0,
    big_chances_missed: s.bigChancesMissed || 0,
    hit_woodwork: s.hitWoodwork || 0,
    fast_break_shots: s.fastBreakShots || 0,
    free_kick_shots: s.freeKickShots || 0,
    penalties_taken: s.penaltiesTaken || 0,

    // ═══════════════════════════════════════════════════════════
    // TIROS POR PARTIDO
    // ═══════════════════════════════════════════════════════════
    shots_per_game: safeDiv(s.shots || 0, matches),
    shots_on_target_per_game: safeDiv(s.shotsOnTarget || 0, matches),
    shots_off_target_per_game: safeDiv(s.shotsOffTarget || 0, matches),
    shots_blocked_per_game: safeDiv(s.blockedScoringAttempt || 0, matches),
    shots_inside_box_per_game: safeDiv(s.shotsFromInsideTheBox || 0, matches),
    shots_outside_box_per_game: safeDiv(s.shotsFromOutsideTheBox || 0, matches),
    big_chances_per_game: safeDiv(s.bigChances || 0, matches),
    big_chances_created_per_game: safeDiv(s.bigChancesCreated || 0, matches),
    big_chances_missed_per_game: safeDiv(s.bigChancesMissed || 0, matches),
    hit_woodwork_per_game: safeDiv(s.hitWoodwork || 0, matches),
    fast_break_shots_per_game: safeDiv(s.fastBreakShots || 0, matches),
    free_kick_shots_per_game: safeDiv(s.freeKickShots || 0, matches),

    // ═══════════════════════════════════════════════════════════
    // PASES
    // ═══════════════════════════════════════════════════════════
    total_passes: s.totalPasses || 0,
    accurate_passes: s.accuratePasses || 0,
    pass_accuracy: s.accuratePassesPercentage || 0,
    total_own_half_passes: s.totalOwnHalfPasses || 0,
    accurate_own_half_passes: s.accurateOwnHalfPasses || 0,
    pass_accuracy_own_half: s.accurateOwnHalfPassesPercentage || 0,
    total_opp_half_passes: s.totalOppositionHalfPasses || 0,
    accurate_opp_half_passes: s.accurateOppositionHalfPasses || 0,
    pass_accuracy_opp_half: s.accurateOppositionHalfPassesPercentage || 0,
    total_long_balls: s.totalLongBalls || 0,
    accurate_long_balls: s.accurateLongBalls || 0,
    long_ball_accuracy: s.accurateLongBallsPercentage || 0,
    total_crosses: s.totalCrosses || 0,
    accurate_crosses: s.accurateCrosses || 0,
    cross_accuracy: s.accurateCrossesPercentage || 0,

    // ═══════════════════════════════════════════════════════════
    // PASES POR PARTIDO
    // ═══════════════════════════════════════════════════════════
    passes_total_per_game: safeDiv(s.totalPasses || 0, matches),
    passes_completed_per_game: safeDiv(s.accuratePasses || 0, matches),
    passes_opp_half_total_per_game: safeDiv(
      s.totalOppositionHalfPasses || 0,
      matches,
    ),
    passes_opp_half_per_game: safeDiv(
      s.accurateOppositionHalfPasses || 0,
      matches,
    ),
    long_balls_total_per_game: safeDiv(s.totalLongBalls || 0, matches),
    long_balls_per_game: safeDiv(s.accurateLongBalls || 0, matches),
    crosses_total_per_game: safeDiv(s.totalCrosses || 0, matches),
    crosses_per_game: safeDiv(s.accurateCrosses || 0, matches),

    // ═══════════════════════════════════════════════════════════
    // ACCIONES OFENSIVAS
    // ═══════════════════════════════════════════════════════════
    successful_dribbles: s.successfulDribbles || 0,
    dribble_attempts: s.dribbleAttempts || 0,
    dribble_success_pct:
      safeDiv(s.successfulDribbles || 0, s.dribbleAttempts || 1) * 100,
    corners: s.corners || 0,
    corners_per_game: safeDiv(s.corners || 0, matches),
    fast_breaks: s.fastBreaks || 0,
    fast_breaks_per_game: safeDiv(s.fastBreaks || 0, matches),
    throw_ins: s.throwIns || 0,
    throw_ins_per_game: safeDiv(s.throwIns || 0, matches),
    ball_recovery: s.ballRecovery || 0,
    ball_recovery_per_game: safeDiv(s.ballRecovery || 0, matches),
    free_kicks: s.freeKicks || 0,
    free_kicks_per_game: safeDiv(s.freeKicks || 0, matches),

    // ═══════════════════════════════════════════════════════════
    // POSESIÓN
    // ═══════════════════════════════════════════════════════════
    // ── Issue #3: usar null en lugar de 50 si el dato no existe ──
    possession_pct: s.averageBallPossession ?? null,
    possession_lost: s.possessionLost || 0,
    possession_lost_per_game: safeDiv(s.possessionLost || 0, matches),

    // ═══════════════════════════════════════════════════════════
    // PORTERO
    // ═══════════════════════════════════════════════════════════
    saves: s.saves || 0,
    saves_per_game: safeDiv(s.saves || 0, matches),
    save_pct: safeDiv(s.saves || 0, s.shotsOnTargetAgainst || 1) * 100,
    clean_sheets: cleanSheetsTotal,
    clean_sheets_home: cleanSheetsHome,
    clean_sheets_away: cleanSheetsAway,
    goal_kicks: s.goalKicks || 0,
    goal_kicks_per_game: safeDiv(s.goalKicks || 0, matches),

    // ═══════════════════════════════════════════════════════════
    // DEFENSA
    // ═══════════════════════════════════════════════════════════
    tackles: s.tackles || 0,
    tackles_per_game: safeDiv(s.tackles || 0, matches),
    interceptions: s.interceptions || 0,
    interceptions_per_game: safeDiv(s.interceptions || 0, matches),
    clearances: s.clearances || 0,
    clearances_per_game: safeDiv(s.clearances || 0, matches),
    clearances_off_line: s.clearancesOffLine || 0,
    clearances_off_line_per_game: safeDiv(s.clearancesOffLine || 0, matches),
    last_man_tackles: s.lastManTackles || 0,
    last_man_tackles_per_game: safeDiv(s.lastManTackles || 0, matches),

    // ═══════════════════════════════════════════════════════════
    // DUELOS
    // ═══════════════════════════════════════════════════════════
    total_duels: s.totalDuels || 0,
    duels_won: s.duelsWon || 0,
    duels_won_pct: s.duelsWonPercentage || 0,
    duels_won_per_game: safeDiv(s.duelsWon || 0, matches),
    total_ground_duels: s.totalGroundDuels || 0,
    ground_duels_won: s.groundDuelsWon || 0,
    ground_duels_won_pct: s.groundDuelsWonPercentage || 0,
    ground_duels_won_per_game: safeDiv(s.groundDuelsWon || 0, matches),
    total_aerial_duels: s.totalAerialDuels || 0,
    aerial_duels_won: s.aerialDuelsWon || 0,
    aerial_duels_won_pct: s.aerialDuelsWonPercentage || 0,
    aerial_duels_won_per_game: safeDiv(s.aerialDuelsWon || 0, matches),

    // ═══════════════════════════════════════════════════════════
    // DISCIPLINA
    // ═══════════════════════════════════════════════════════════
    fouls: s.fouls || 0,
    fouls_per_game: safeDiv(s.fouls || 0, matches),
    offsides: s.offsides || 0,
    offside_per_game: safeDiv(s.offsides || 0, matches),
    yellow_cards: s.yellowCards || 0,
    yellow_cards_per_game: safeDiv(s.yellowCards || 0, matches),
    yellow_red_cards: s.yellowRedCards || 0,
    red_cards: s.redCards || 0,
    red_cards_total: (s.redCards || 0) + (s.yellowRedCards || 0),
    penalties_conceded: s.penaltiesCommited || 0,
    penalty_goals_conceded: s.penaltyGoalsConceded || 0,
    errors_leading_to_goal: s.errorsLeadingToGoal || 0,
    errors_leading_to_shot: s.errorsLeadingToShot || 0,
    errors_leading_to_goal_per_game: safeDiv(
      s.errorsLeadingToGoal || 0,
      matches,
    ),
    errors_leading_to_shot_per_game: safeDiv(
      s.errorsLeadingToShot || 0,
      matches,
    ),

    // ═══════════════════════════════════════════════════════════
    // FÍSICAS
    // ═══════════════════════════════════════════════════════════
    kilometers_covered: s.kilometersCovered || 0,
    kilometers_covered_per_game: safeDiv(s.kilometersCovered || 0, matches),
    number_of_sprints: s.numberOfSprints || 0,
    sprints_per_game: safeDiv(s.numberOfSprints || 0, matches),

    // ═══════════════════════════════════════════════════════════
    // RATING
    // ═══════════════════════════════════════════════════════════
    // ── Issue #3: usar null en lugar de 6.5 si no hay dato real ──
    avg_rating: s.avgRating || null,

    // ═══════════════════════════════════════════════════════════
    // xG / xGA (Modelo mejorado)
    // ═══════════════════════════════════════════════════════════
    // ── Issue #4: indicar si el xG es real o imputado ──
    xg_per_game: xgPerGame > 0 ? xgPerGame : null,
    xga_per_game: xgaPerGame > 0 ? xgaPerGame : null,
    xg_is_imputed: !hasRealXg,  // true = no proviene de expectedGoals oficial de SofaScore
    // ── Issue #13: has_stats explícito por equipo ──
    has_stats: matches > 0,

    // ═══════════════════════════════════════════════════════════
    // ESTADÍSTICAS CONTRA (OPONENTE)
    // ═══════════════════════════════════════════════════════════
    shots_against: s.shotsAgainst || 0,
    shots_against_per_game: safeDiv(s.shotsAgainst || 0, matches),
    shots_on_target_against: s.shotsOnTargetAgainst || 0,
    shots_on_target_against_per_game: safeDiv(
      s.shotsOnTargetAgainst || 0,
      matches,
    ),
    shots_off_target_against: s.shotsOffTargetAgainst || 0,
    shots_off_target_against_per_game: safeDiv(
      s.shotsOffTargetAgainst || 0,
      matches,
    ),
    shots_blocked_against: s.shotsBlockedAgainst || 0,
    shots_blocked_against_per_game: safeDiv(
      s.shotsBlockedAgainst || 0,
      matches,
    ),
    blocked_scoring_attempt_against: s.blockedScoringAttemptAgainst || 0,
    blocked_scoring_attempt_against_per_game: safeDiv(
      s.blockedScoringAttemptAgainst || 0,
      matches,
    ),
    shots_inside_box_against: s.shotsFromInsideTheBoxAgainst || 0,
    shots_inside_box_against_per_game: safeDiv(
      s.shotsFromInsideTheBoxAgainst || 0,
      matches,
    ),
    shots_outside_box_against: s.shotsFromOutsideTheBoxAgainst || 0,
    shots_outside_box_against_per_game: safeDiv(
      s.shotsFromOutsideTheBoxAgainst || 0,
      matches,
    ),
    big_chances_against: s.bigChancesAgainst || 0,
    big_chances_against_per_game: safeDiv(s.bigChancesAgainst || 0, matches),
    big_chances_created_against: s.bigChancesCreatedAgainst || 0,
    big_chances_created_against_per_game: safeDiv(
      s.bigChancesCreatedAgainst || 0,
      matches,
    ),
    big_chances_missed_against: s.bigChancesMissedAgainst || 0,
    big_chances_missed_against_per_game: safeDiv(
      s.bigChancesMissedAgainst || 0,
      matches,
    ),
    hit_woodwork_against: s.hitWoodworkAgainst || 0,
    hit_woodwork_against_per_game: safeDiv(s.hitWoodworkAgainst || 0, matches),

    // ═══════════════════════════════════════════════════════════
    // PASES CONTRA
    // ═══════════════════════════════════════════════════════════
    total_passes_against: s.totalPassesAgainst || 0,
    accurate_passes_against: s.accuratePassesAgainst || 0,
    total_own_half_passes_against: s.ownHalfPassesTotalAgainst || 0,
    accurate_own_half_passes_against: s.accurateOwnHalfPassesAgainst || 0,
    total_opp_half_passes_against: s.oppositionHalfPassesTotalAgainst || 0,
    accurate_opp_half_passes_against:
      s.accurateOppositionHalfPassesAgainst || 0,
    total_final_third_passes_against: s.totalFinalThirdPassesAgainst || 0,
    accurate_final_third_passes_against: s.accurateFinalThirdPassesAgainst || 0,
    crosses_total_against: s.crossesTotalAgainst || 0,
    crosses_successful_against: s.crossesSuccessfulAgainst || 0,
    long_balls_total_against: s.longBallsTotalAgainst || 0,
    long_balls_successful_against: s.longBallsSuccessfulAgainst || 0,

    // ═══════════════════════════════════════════════════════════
    // ACCIONES CONTRA
    // ═══════════════════════════════════════════════════════════
    dribble_attempts_against: s.dribbleAttemptsTotalAgainst || 0,
    dribble_attempts_won_against: s.dribbleAttemptsWonAgainst || 0,
    tackles_against: s.tacklesAgainst || 0,
    interceptions_against: s.interceptionsAgainst || 0,
    clearances_against: s.clearancesAgainst || 0,
    key_passes_against: s.keyPassesAgainst || 0,
    corners_against: s.cornersAgainst || 0,
    corners_conceded_per_game: safeDiv(s.cornersAgainst || 0, matches),
    offsides_against: s.offsidesAgainst || 0,
    yellow_cards_against: s.yellowCardsAgainst || 0,
    red_cards_against: s.redCardsAgainst || 0,
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
            scoresAgainst: row.scoresAgainst,
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
function buildLeagueStats(standings, refereeStats, leagueInfo = null) {
  let totalMatches = 0;
  let avgGoals = 2.74;
  let avgYellow = 4.0;
  let avgRed = 0.2;
  let avgCorners = 9.5;
  let avgShots = 26.0;
  let avgShotsTarget = 8.5;
  let homeWinPct = 45.0;
  let drawPct = 25.0;
  let awayWinPct = 30.0;
  let homeAdvantage = 1.2;
  let awayDisadvantage = 0.85;

  // Use leagueInfo if available
  if (leagueInfo && leagueInfo.info) {
    const info = leagueInfo.info;
    const winsH = info.homeTeamWins || 0;
    const winsA = info.awayTeamWins || 0;
    const draws = info.draws || 0;
    const matchesCount = winsH + winsA + draws;
    if (matchesCount > 0) {
      totalMatches = matchesCount;
      if (info.goals != null) {
        avgGoals = info.goals / matchesCount;
      }
      if (info.yellowCards != null) {
        avgYellow = info.yellowCards / matchesCount;
      }
      if (info.redCards != null) {
        avgRed = info.redCards / matchesCount;
      }
      if (info.cornerKicks != null) {
        avgCorners = info.cornerKicks / matchesCount;
      }
      if (info.shots != null) {
        avgShots = info.shots / matchesCount;
      }
      if (info.shotsOnTarget != null) {
        avgShotsTarget = info.shotsOnTarget / matchesCount;
      }

      // ── Issue #9: 1X2 reales de la liga ──
      homeWinPct = (winsH / matchesCount) * 100;
      drawPct = (draws / matchesCount) * 100;
      awayWinPct = (winsA / matchesCount) * 100;

      // ── Issue #9: Factor local/visitante derivado por goles cuando estén disponibles, o por victorias ──
      const homeGoals = info.homeTeamGoals ?? null;
      const awayGoals = info.awayTeamGoals ?? null;
      if (homeGoals != null && awayGoals != null && (homeGoals + awayGoals) > 0) {
        const totalG = homeGoals + awayGoals;
        homeAdvantage = Math.min(1.4, Math.max(1.05, (homeGoals / (totalG / 2))));
        awayDisadvantage = Math.min(0.95, Math.max(0.65, (awayGoals / (totalG / 2))));
      } else {
        const diffWinsRatio = (winsH - winsA) / matchesCount;
        homeAdvantage = Math.min(1.4, Math.max(1.05, 1.0 + diffWinsRatio));
        awayDisadvantage = Math.min(0.95, Math.max(0.65, 1.0 - diffWinsRatio));
      }
    }
  }

  // Fallback to standings for matches/goals/1X2 if leagueInfo wasn't present or complete
  if (totalMatches === 0 && standings && standings.standings) {
    let totalGoalsFor = 0;
    let totalHomeWins = 0;
    let totalAwayWins = 0;
    let totalDraws = 0;
    let homeGoalsTotal = 0;
    let awayGoalsTotal = 0;
    let hasHomeAwayBreakdown = false;

    for (const group of standings.standings) {
      if (group.rows) {
        for (const row of group.rows) {
          totalMatches += row.matches || 0;
          totalGoalsFor += row.scoresFor || 0;
          if (row.home) {
            hasHomeAwayBreakdown = true;
            totalHomeWins += row.home.wins || 0;
            totalDraws += row.home.draws || 0;
            homeGoalsTotal += row.home.scoresFor || 0;
          }
          if (row.away) {
            totalAwayWins += row.away.wins || 0;
            awayGoalsTotal += row.away.scoresFor || 0;
          }
        }
      }
    }
    const actualMatches = totalMatches / 2;
    if (actualMatches > 0) {
      avgGoals = totalGoalsFor / actualMatches;
      if (hasHomeAwayBreakdown && (totalHomeWins + totalAwayWins + totalDraws) > 0) {
        const countedMatches = totalHomeWins + totalAwayWins + totalDraws;
        homeWinPct = (totalHomeWins / countedMatches) * 100;
        drawPct = (totalDraws / countedMatches) * 100;
        awayWinPct = (totalAwayWins / countedMatches) * 100;
        if (homeGoalsTotal > 0 && awayGoalsTotal > 0) {
          const expectedPerSide = (homeGoalsTotal + awayGoalsTotal) / 2;
          homeAdvantage = Math.min(1.4, Math.max(1.05, homeGoalsTotal / expectedPerSide));
          awayDisadvantage = Math.min(0.95, Math.max(0.65, awayGoalsTotal / expectedPerSide));
        }
      }
    }
  }

  return {
    avg_goals_per_game: avgGoals,
    avg_corners_per_game: avgCorners,
    avg_yellow_cards_per_game: avgYellow,
    avg_red_cards_per_game: avgRed,
    avg_cards_per_game: avgYellow + avgRed,
    avg_shots_per_game: avgShots,
    avg_shots_target_per_game: avgShotsTarget,
    home_win_pct: homeWinPct,
    draw_pct: drawPct,
    away_win_pct: awayWinPct,
    home_advantage_factor: homeAdvantage,
    away_disadvantage_factor: awayDisadvantage,
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

  if (!match) {
    throw new Error("Datos incompletos: se requiere match");
  }

  const homeName = match.homeTeam?.shortName || match.homeTeam?.name || "Local";
  const awayName =
    match.awayTeam?.shortName || match.awayTeam?.name || "Visitante";

  // Fix: Asegurar la correcta extracción de competition desde el evento
  const competition =
    match.tournament?.uniqueTournament?.name ||
    match.event?.tournament?.uniqueTournament?.name ||
    "Desconocida";

  const homeTeamId = match.homeTeam?.id;
  const awayTeamId = match.awayTeam?.id;

  // Si no hay estadísticas de equipo (ej. inicio de liga), construir una estructura base vacía con 0 partidos
  const home = homeStats
    ? mapSofaScoreToSherlockTeamStats(
        homeStats,
        homeName,
        true,
        standings,
        homeTeamId,
      )
    : {
        // ═══════════════════════════════════════════════════════════
        // ESTADÍSTICAS BÁSICAS
        // ═══════════════════════════════════════════════════════════
        name: homeName,
        matches_home: 0,
        matches_away: 0,
        matches_played: 0,
        wins: 0,
        draws: 0,
        losses: 0,

        // ═══════════════════════════════════════════════════════════
        // GOLES
        // ═══════════════════════════════════════════════════════════
        goals_scored: 0,
        goals_conceded: 0,
        own_goals: 0,
        assists: 0,
        goals_inside_box: 0,
        goals_outside_box: 0,
        headed_goals: 0,
        left_foot_goals: 0,
        right_foot_goals: 0,
        free_kick_goals: 0,
        fast_break_goals: 0,
        penalty_goals: 0,

        // ═══════════════════════════════════════════════════════════
        // GOLES POR PARTIDO
        // ═══════════════════════════════════════════════════════════
        goals_per_game: 0,
        goals_conceded_per_game: 0,
        goal_conversion_pct: 0,

        // ═══════════════════════════════════════════════════════════
        // TIROS
        // ═══════════════════════════════════════════════════════════
        shots: 0,
        shots_on_target: 0,
        shots_off_target: 0,
        shots_blocked: 0,
        shots_inside_box: 0,
        shots_outside_box: 0,
        big_chances: 0,
        big_chances_created: 0,
        big_chances_missed: 0,
        hit_woodwork: 0,
        fast_break_shots: 0,
        free_kick_shots: 0,
        penalties_taken: 0,

        // ═══════════════════════════════════════════════════════════
        // TIROS POR PARTIDO
        // ═══════════════════════════════════════════════════════════
        shots_per_game: 0,
        shots_on_target_per_game: 0,
        shots_off_target_per_game: 0,
        shots_blocked_per_game: 0,
        shots_inside_box_per_game: 0,
        shots_outside_box_per_game: 0,
        big_chances_per_game: 0,
        big_chances_created_per_game: 0,
        big_chances_missed_per_game: 0,
        hit_woodwork_per_game: 0,
        fast_break_shots_per_game: 0,
        free_kick_shots_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // PASES
        // ═══════════════════════════════════════════════════════════
        total_passes: 0,
        accurate_passes: 0,
        pass_accuracy: 0,
        total_own_half_passes: 0,
        accurate_own_half_passes: 0,
        pass_accuracy_own_half: 0,
        total_opp_half_passes: 0,
        accurate_opp_half_passes: 0,
        pass_accuracy_opp_half: 0,
        total_long_balls: 0,
        accurate_long_balls: 0,
        long_ball_accuracy: 0,
        total_crosses: 0,
        accurate_crosses: 0,
        cross_accuracy: 0,

        // ═══════════════════════════════════════════════════════════
        // PASES POR PARTIDO
        // ═══════════════════════════════════════════════════════════
        passes_total_per_game: 0,
        passes_completed_per_game: 0,
        passes_opp_half_total_per_game: 0,
        passes_opp_half_per_game: 0,
        long_balls_total_per_game: 0,
        long_balls_per_game: 0,
        crosses_total_per_game: 0,
        crosses_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // ACCIONES OFENSIVAS
        // ═══════════════════════════════════════════════════════════
        successful_dribbles: 0,
        dribble_attempts: 0,
        dribble_success_pct: 0,
        corners: 0,
        corners_per_game: 0,
        fast_breaks: 0,
        fast_breaks_per_game: 0,
        throw_ins: 0,
        throw_ins_per_game: 0,
        ball_recovery: 0,
        ball_recovery_per_game: 0,
        free_kicks: 0,
        free_kicks_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // POSESIÓN
        // ═══════════════════════════════════════════════════════════
        possession_pct: null,
        possession_lost: 0,
        possession_lost_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // PORTERO
        // ═══════════════════════════════════════════════════════════
        saves: 0,
        saves_per_game: 0,
        save_pct: 0,
        clean_sheets: 0,
        clean_sheets_home: 0,
        clean_sheets_away: 0,
        goal_kicks: 0,
        goal_kicks_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // DEFENSA
        // ═══════════════════════════════════════════════════════════
        tackles: 0,
        tackles_per_game: 0,
        interceptions: 0,
        interceptions_per_game: 0,
        clearances: 0,
        clearances_per_game: 0,
        clearances_off_line: 0,
        clearances_off_line_per_game: 0,
        last_man_tackles: 0,
        last_man_tackles_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // DUELOS
        // ═══════════════════════════════════════════════════════════
        total_duels: 0,
        duels_won: 0,
        duels_won_pct: 50,
        duels_won_per_game: 0,
        total_ground_duels: 0,
        ground_duels_won: 0,
        ground_duels_won_pct: 50,
        ground_duels_won_per_game: 0,
        total_aerial_duels: 0,
        aerial_duels_won: 0,
        aerial_duels_won_pct: 50,
        aerial_duels_won_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // DISCIPLINA
        // ═══════════════════════════════════════════════════════════
        fouls: 0,
        fouls_per_game: 0,
        offsides: 0,
        offside_per_game: 0,
        yellow_cards: 0,
        yellow_cards_per_game: 0,
        yellow_red_cards: 0,
        red_cards: 0,
        red_cards_total: 0,
        penalties_conceded: 0,
        penalty_goals_conceded: 0,
        errors_leading_to_goal: 0,
        errors_leading_to_shot: 0,
        errors_leading_to_goal_per_game: 0,
        errors_leading_to_shot_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // FÍSICAS
        // ═══════════════════════════════════════════════════════════
        kilometers_covered: 0,
        kilometers_covered_per_game: 0,
        number_of_sprints: 0,
        sprints_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // RATING
        // ═══════════════════════════════════════════════════════════
        avg_rating: null,  // Issue #3: null, no 6.5

        // ═══════════════════════════════════════════════════════════
        // xG / xGA
        // ═══════════════════════════════════════════════════════════
        xg_per_game: null,
        xga_per_game: null,
        xg_is_imputed: true,  // Issue #4: sin xG real
        // Issue #13: sin datos de equipo
        has_stats: false,

        // ═══════════════════════════════════════════════════════════
        // ESTADÍSTICAS CONTRA
        // ═══════════════════════════════════════════════════════════
        shots_against: 0,
        shots_against_per_game: 0,
        shots_on_target_against: 0,
        shots_on_target_against_per_game: 0,
        shots_off_target_against: 0,
        shots_off_target_against_per_game: 0,
        shots_blocked_against: 0,
        shots_blocked_against_per_game: 0,
        blocked_scoring_attempt_against: 0,
        blocked_scoring_attempt_against_per_game: 0,
        shots_inside_box_against: 0,
        shots_inside_box_against_per_game: 0,
        shots_outside_box_against: 0,
        shots_outside_box_against_per_game: 0,
        big_chances_against: 0,
        big_chances_against_per_game: 0,
        big_chances_created_against: 0,
        big_chances_created_against_per_game: 0,
        big_chances_missed_against: 0,
        big_chances_missed_against_per_game: 0,
        hit_woodwork_against: 0,
        hit_woodwork_against_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // PASES CONTRA
        // ═══════════════════════════════════════════════════════════
        total_passes_against: 0,
        accurate_passes_against: 0,
        total_own_half_passes_against: 0,
        accurate_own_half_passes_against: 0,
        total_opp_half_passes_against: 0,
        accurate_opp_half_passes_against: 0,
        total_final_third_passes_against: 0,
        accurate_final_third_passes_against: 0,
        crosses_total_against: 0,
        crosses_successful_against: 0,
        long_balls_total_against: 0,
        long_balls_successful_against: 0,

        // ═══════════════════════════════════════════════════════════
        // ACCIONES CONTRA
        // ═══════════════════════════════════════════════════════════
        dribble_attempts_against: 0,
        dribble_attempts_won_against: 0,
        tackles_against: 0,
        interceptions_against: 0,
        clearances_against: 0,
        key_passes_against: 0,
        corners_against: 0,
        corners_conceded_per_game: 0,
        offsides_against: 0,
        yellow_cards_against: 0,
        red_cards_against: 0,
      };

  const away = awayStats
    ? mapSofaScoreToSherlockTeamStats(
        awayStats,
        awayName,
        false,
        standings,
        awayTeamId,
      )
    : {
        // ═══════════════════════════════════════════════════════════
        // ESTADÍSTICAS BÁSICAS
        // ═══════════════════════════════════════════════════════════
        name: awayName,
        matches_home: 0,
        matches_away: 0,
        matches_played: 0,
        wins: 0,
        draws: 0,
        losses: 0,

        // ═══════════════════════════════════════════════════════════
        // GOLES
        // ═══════════════════════════════════════════════════════════
        goals_scored: 0,
        goals_conceded: 0,
        own_goals: 0,
        assists: 0,
        goals_inside_box: 0,
        goals_outside_box: 0,
        headed_goals: 0,
        left_foot_goals: 0,
        right_foot_goals: 0,
        free_kick_goals: 0,
        fast_break_goals: 0,
        penalty_goals: 0,

        // ═══════════════════════════════════════════════════════════
        // GOLES POR PARTIDO
        // ═══════════════════════════════════════════════════════════
        goals_per_game: 0,
        goals_conceded_per_game: 0,
        goal_conversion_pct: 0,

        // ═══════════════════════════════════════════════════════════
        // TIROS
        // ═══════════════════════════════════════════════════════════
        shots: 0,
        shots_on_target: 0,
        shots_off_target: 0,
        shots_blocked: 0,
        shots_inside_box: 0,
        shots_outside_box: 0,
        big_chances: 0,
        big_chances_created: 0,
        big_chances_missed: 0,
        hit_woodwork: 0,
        fast_break_shots: 0,
        free_kick_shots: 0,
        penalties_taken: 0,

        // ═══════════════════════════════════════════════════════════
        // TIROS POR PARTIDO
        // ═══════════════════════════════════════════════════════════
        shots_per_game: 0,
        shots_on_target_per_game: 0,
        shots_off_target_per_game: 0,
        shots_blocked_per_game: 0,
        shots_inside_box_per_game: 0,
        shots_outside_box_per_game: 0,
        big_chances_per_game: 0,
        big_chances_created_per_game: 0,
        big_chances_missed_per_game: 0,
        hit_woodwork_per_game: 0,
        fast_break_shots_per_game: 0,
        free_kick_shots_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // PASES
        // ═══════════════════════════════════════════════════════════
        total_passes: 0,
        accurate_passes: 0,
        pass_accuracy: 0,
        total_own_half_passes: 0,
        accurate_own_half_passes: 0,
        pass_accuracy_own_half: 0,
        total_opp_half_passes: 0,
        accurate_opp_half_passes: 0,
        pass_accuracy_opp_half: 0,
        total_long_balls: 0,
        accurate_long_balls: 0,
        long_ball_accuracy: 0,
        total_crosses: 0,
        accurate_crosses: 0,
        cross_accuracy: 0,

        // ═══════════════════════════════════════════════════════════
        // PASES POR PARTIDO
        // ═══════════════════════════════════════════════════════════
        passes_total_per_game: 0,
        passes_completed_per_game: 0,
        passes_opp_half_total_per_game: 0,
        passes_opp_half_per_game: 0,
        long_balls_total_per_game: 0,
        long_balls_per_game: 0,
        crosses_total_per_game: 0,
        crosses_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // ACCIONES OFENSIVAS
        // ═══════════════════════════════════════════════════════════
        successful_dribbles: 0,
        dribble_attempts: 0,
        dribble_success_pct: 0,
        corners: 0,
        corners_per_game: 0,
        fast_breaks: 0,
        fast_breaks_per_game: 0,
        throw_ins: 0,
        throw_ins_per_game: 0,
        ball_recovery: 0,
        ball_recovery_per_game: 0,
        free_kicks: 0,
        free_kicks_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // POSESIÓN
        // ═══════════════════════════════════════════════════════════
        possession_pct: null,
        possession_lost: 0,
        possession_lost_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // PORTERO
        // ═══════════════════════════════════════════════════════════
        saves: 0,
        saves_per_game: 0,
        save_pct: 0,
        clean_sheets: 0,
        clean_sheets_home: 0,
        clean_sheets_away: 0,
        goal_kicks: 0,
        goal_kicks_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // DEFENSA
        // ═══════════════════════════════════════════════════════════
        tackles: 0,
        tackles_per_game: 0,
        interceptions: 0,
        interceptions_per_game: 0,
        clearances: 0,
        clearances_per_game: 0,
        clearances_off_line: 0,
        clearances_off_line_per_game: 0,
        last_man_tackles: 0,
        last_man_tackles_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // DUELOS
        // ═══════════════════════════════════════════════════════════
        total_duels: 0,
        duels_won: 0,
        duels_won_pct: 50,
        duels_won_per_game: 0,
        total_ground_duels: 0,
        ground_duels_won: 0,
        ground_duels_won_pct: 50,
        ground_duels_won_per_game: 0,
        total_aerial_duels: 0,
        aerial_duels_won: 0,
        aerial_duels_won_pct: 50,
        aerial_duels_won_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // DISCIPLINA
        // ═══════════════════════════════════════════════════════════
        fouls: 0,
        fouls_per_game: 0,
        offsides: 0,
        offside_per_game: 0,
        yellow_cards: 0,
        yellow_cards_per_game: 0,
        yellow_red_cards: 0,
        red_cards: 0,
        red_cards_total: 0,
        penalties_conceded: 0,
        penalty_goals_conceded: 0,
        errors_leading_to_goal: 0,
        errors_leading_to_shot: 0,
        errors_leading_to_goal_per_game: 0,
        errors_leading_to_shot_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // FÍSICAS
        // ═══════════════════════════════════════════════════════════
        kilometers_covered: 0,
        kilometers_covered_per_game: 0,
        number_of_sprints: 0,
        sprints_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // RATING
        // ═══════════════════════════════════════════════════════════
        avg_rating: null,

        // ═══════════════════════════════════════════════════════════
        // xG / xGA
        // ═══════════════════════════════════════════════════════════
        xg_per_game: null,
        xga_per_game: null,
        xg_is_imputed: true,
        has_stats: false,

        // ═══════════════════════════════════════════════════════════
        // ESTADÍSTICAS CONTRA
        // ═══════════════════════════════════════════════════════════
        shots_against: 0,
        shots_against_per_game: 0,
        shots_on_target_against: 0,
        shots_on_target_against_per_game: 0,
        shots_off_target_against: 0,
        shots_off_target_against_per_game: 0,
        shots_blocked_against: 0,
        shots_blocked_against_per_game: 0,
        blocked_scoring_attempt_against: 0,
        blocked_scoring_attempt_against_per_game: 0,
        shots_inside_box_against: 0,
        shots_inside_box_against_per_game: 0,
        shots_outside_box_against: 0,
        shots_outside_box_against_per_game: 0,
        big_chances_against: 0,
        big_chances_against_per_game: 0,
        big_chances_created_against: 0,
        big_chances_created_against_per_game: 0,
        big_chances_missed_against: 0,
        big_chances_missed_against_per_game: 0,
        hit_woodwork_against: 0,
        hit_woodwork_against_per_game: 0,

        // ═══════════════════════════════════════════════════════════
        // PASES CONTRA
        // ═══════════════════════════════════════════════════════════
        total_passes_against: 0,
        accurate_passes_against: 0,
        total_own_half_passes_against: 0,
        accurate_own_half_passes_against: 0,
        total_opp_half_passes_against: 0,
        accurate_opp_half_passes_against: 0,
        total_final_third_passes_against: 0,
        accurate_final_third_passes_against: 0,
        crosses_total_against: 0,
        crosses_successful_against: 0,
        long_balls_total_against: 0,
        long_balls_successful_against: 0,

        // ═══════════════════════════════════════════════════════════
        // ACCIONES CONTRA
        // ═══════════════════════════════════════════════════════════
        dribble_attempts_against: 0,
        dribble_attempts_won_against: 0,
        tackles_against: 0,
        interceptions_against: 0,
        clearances_against: 0,
        key_passes_against: 0,
        corners_against: 0,
        corners_conceded_per_game: 0,
        offsides_against: 0,
        yellow_cards_against: 0,
        red_cards_against: 0,
      };

  const refereeStats = extractRefereeStats(match);
  const leagueStats = buildLeagueStats(
    standings,
    refereeStats,
    extractedData.leagueInfo,
  );

  const odds = {
    home: null,
    draw: null,
    away: null,
    btts_yes: null,
    btts_no: null,
    dc_1x: null,
    dc_x2: null,
    dc_12: null,
    goals_lines: ["1.5", "2.5", "3.5", "4.5"],
    goalsOverOdds: {},
    goalsUnderOdds: {},
    corners_lines: ["7.5", "8.5", "9.5", "10.5"],
    cornersOverOdds: {},
    cornersUnderOdds: {},
    cards_lines: ["2.5", "3.5", "4.5", "5.5"],
    cardsOverOdds: {},
    cardsUnderOdds: {},
    shots_lines: ["21.5", "22.5", "23.5", "24.5"],
    shotsOverOdds: {},
    shotsUnderOdds: {},
    shots_target_lines: ["7.5", "8.5", "9.5", "10.5"],
    shotsTargetOverOdds: {},
    shotsTargetUnderOdds: {},
    bookmaker: "",
  };

  // ── Issue #11: normalizar temporada ──
  const rawSeason = match.season?.year || match.season?.name || null;
  const normalizedSeason = rawSeason
    ? String(rawSeason).replace(/^(\d{2})\/(\d{2})$/, (_, a, b) => `20${a}/20${b}`)
    : rawSeason;

  return {
    sport: "football",
    home: home,
    away: away,
    odds: odds,
    league_stats: leagueStats,
    competition: competition,
    generate_llm_analysis: false,
    user_context: "",
    // ── Issue #13: has_stats a nivel partido y por equipo ──
    has_real_stats: !!(homeStats && awayStats),
    home_has_stats: home.has_stats ?? !!(homeStats),
    away_has_stats: away.has_stats ?? !!(awayStats),
    start_timestamp: match.startTimestamp,
    // ── Issue #11: enviar match_date en UTC y extractedAt ──
    match_date: match.startTimestamp
      ? new Date(match.startTimestamp * 1000).toISOString()
      : null,
    extracted_at: new Date().toISOString(),
    season: normalizedSeason,
    // ── Issue #10: IDs de torneo y temporada ──
    tournament_id: match.tournament?.id || null,
    unique_tournament_id: match.tournament?.uniqueTournament?.id || null,
    season_id: extractedData.seasonId || null,
    country: match.tournament?.uniqueTournament?.category?.country?.name || null,
    // ── Issue #12: no descartar alineaciones y rachas descargadas ──
    lineups: extractedData.lineups || null,
    team_streaks: extractedData.teamStreaks || null,
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
