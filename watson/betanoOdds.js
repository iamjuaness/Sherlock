// betanoOdds.js - Búsqueda y parseo de cuotas de Betano (sin visitar el partido)
// Se carga en el Service Worker (background.js) vía importScripts("betanoOdds.js")
// ═══════════════════════════════════════════════════════════════
// NORMALIZACIÓN / MATCHING DE EQUIPOS
// ═══════════════════════════════════════════════════════════════
function normalizeTeamName(str) {
  return (str || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // quita tildes
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(
      /\b(fc|cf|sc|cd|ac|club|deportivo|atletico|real|de|do|el|la)\b/g,
      " ",
    )
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Dado un equipo que puede venir como string ("River Plate") o como objeto
 * { name, shortName } (tal como lo entrega SofaScore), devuelve un array
 * con TODAS las variantes de nombre disponibles, sin duplicados, en orden
 * de preferencia (shortName primero, luego name).
 *
 * Este es el corazón del fallback: en vez de elegir "shortName || name" y
 * quedarnos con uno solo, probamos ambos en cascada.
 */
function getNameVariants(teamOrName) {
  if (!teamOrName) return [];
  if (typeof teamOrName === "string") {
    return teamOrName.trim() ? [teamOrName.trim()] : [];
  }
  const arr = [];
  if (teamOrName.shortName) arr.push(teamOrName.shortName.trim());
  if (teamOrName.name) arr.push(teamOrName.name.trim());
  const seen = new Set();
  return arr.filter((v) => {
    if (!v) return false;
    const key = v.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/** Construye el set de palabras "significativas" (>2 letras) de un conjunto de variantes de nombre */
function buildWordSet(variants) {
  const words = new Set();
  (Array.isArray(variants) ? variants : [variants]).forEach((v) => {
    normalizeTeamName(v)
      .split(" ")
      .filter((w) => w.length > 2)
      .forEach((w) => words.add(w));
  });
  return [...words];
}

/**
 * Elige el mejor evento de Betano dado un listado de resultados de /api/search/
 * (o de nuestro fallback de liga, ver fetchBetanoLeagueEvents).
 *
 * IMPORTANTE (fix): antes se aceptaba un evento con bestScore >= 2 aunque
 * esas 2+ coincidencias vinieran TODAS del mismo lado (ej. "universidad" +
 * "catolica" matcheando solo al rival, cuando el equipo local real no tiene
 * nada que ver). Esto causaba falsos positivos con nombres ambiguos que se
 * repiten en varios países (Universidad Católica CHI/ECU, River Plate, etc).
 * Ahora exigimos homeHit AND awayHit obligatoriamente — no basta el score.
 */
function pickBestBetanoEvent(events, homeVariants, awayVariants) {
  const homeWords = buildWordSet(homeVariants);
  const awayWords = buildWordSet(awayVariants);

  let best = null;
  let bestScore = 0;

  (events || []).forEach((ev) => {
    const label = normalizeTeamName(ev.label || ev.labelLatin || "");
    let score = 0;
    let homeHit = false;
    let awayHit = false;

    homeWords.forEach((w) => {
      if (label.includes(w)) {
        score++;
        homeHit = true;
      }
    });
    awayWords.forEach((w) => {
      if (label.includes(w)) {
        score++;
        awayHit = true;
      }
    });

    // Requisito estricto: AMBOS lados deben matchear, sin excepción.
    if (!homeHit || !awayHit) return;

    score += 2; // bonus por matchear ambos lados

    if (score > bestScore) {
      bestScore = score;
      best = ev;
    }
  });

  return best;
}

/** Extrae { slug, id } desde el campo "url" que devuelve /api/search/ (o el fallback de liga) */
function extractSlugIdFromEvent(ev) {
  if (ev.url) {
    const m = ev.url.match(/\/cuotas-de-partido\/([^\/]+)\/(\d+)/);
    if (m) return { slug: m[1], id: m[2] };
  }
  if (ev.filter && ev.filter.eventId) {
    const slugGuess = (ev.label || "")
      .toLowerCase()
      .replace(/\s*\|.*$/, "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9\s-]/g, "")
      .trim()
      .replace(/\s+/g, "-");
    return { slug: slugGuess, id: ev.filter.eventId };
  }
  return null;
}

// ═══════════════════════════════════════════════════════════════
// FETCH A LA API DE BETANO
// ═══════════════════════════════════════════════════════════════
async function fetchBetanoSearch(term) {
  const url = `https://www.betano.co/api/search/?term=${encodeURIComponent(term)}`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} en búsqueda de Betano`);
  }
  const json = await response.json();
  return (json?.data?.results || []).filter((r) => r.level === "event");
}

// ═══════════════════════════════════════════════════════════════
// FALLBACK DE LIGAS QUE /api/search/ NO INDEXA BIEN
// ═══════════════════════════════════════════════════════════════
const BETANO_LEAGUE_FALLBACKS = [
  {
    match: /bolivia|divisi[oó]n\s*profesional/i,
    url: "https://www.betano.co/api/sport/futbol/bolivia/division-profesional/18274/?req=la,s,stnf,c,mb",
  },
];

function getBetanoLeagueFallbackUrl(leagueName) {
  if (!leagueName) return null;
  const found = BETANO_LEAGUE_FALLBACKS.find((f) => f.match.test(leagueName));
  return found ? found.url : null;
}

async function fetchBetanoLeagueEvents(leagueUrl) {
  const response = await fetch(leagueUrl, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} en fallback de liga de Betano`);
  }
  const json = await response.json();
  const blocks = json?.data?.blocks || [];
  const events = [];
  blocks.forEach((b) => (b.events || []).forEach((e) => events.push(e)));

  return events.map((e) => ({
    label: e.name || e.shortName || "",
    labelLatin: e.shortName || "",
    url: e.url || "",
    filter: null,
  }));
}

// ═══════════════════════════════════════════════════════════════
// parseBetanoOdds
// ═══════════════════════════════════════════════════════════════
function parseBetanoOdds(eventData) {
  const odds = {
    bookmaker: "betano",
    homeTeam: null,
    awayTeam: null,
    home: null,
    draw: null,
    away: null,
    bttsYes: null,
    bttsNo: null,
    dc1X: null,
    dcX2: null,
    dc12: null,

    goalsLines: [],
    goalsOverOdds: {},
    goalsUnderOdds: {},
    cornersLines: [],
    cornersOverOdds: {},
    cornersUnderOdds: {},
    cardsLines: [],
    cardsOverOdds: {},
    cardsUnderOdds: {},
    shotsLines: [],
    shotsOverOdds: {},
    shotsUnderOdds: {},
    shotsTargetLines: [],
    shotsTargetOverOdds: {},
    shotsTargetUnderOdds: {},
  };

  const nameParts = (eventData.shortName || eventData.name || "")
    .split(" - ")
    .map((s) => s.trim());
  odds.homeTeam = nameParts[0] || "Local";
  odds.awayTeam = nameParts[1] || "Visitante";

  const extractOverUnder = (market, linesArr, overDict, underDict) => {
    if (!Array.isArray(market.selections) || market.selections.length === 0)
      return;

    market.selections.forEach((sel) => {
      const line =
        sel.handicap !== undefined && sel.handicap !== null
          ? Number(sel.handicap)
          : null;

      const price = sel.price;

      if (price < 1.1) return;
      if (!line || line === 0) return;
      if (Math.abs((line % 1) - 0.5) > 0.001) return;

      const key = line.toString();
      if (!linesArr.includes(line)) linesArr.push(line);

      if (sel.columnIndex === 0) overDict[key] = sel.price;
      else if (sel.columnIndex === 1) underDict[key] = sel.price;
    });
  };

  eventData.markets.forEach((m) => {
    const mType = (m.type || "").toUpperCase();

    if (
      mType === "MRES" &&
      Array.isArray(m.selections) &&
      m.selections.length >= 3
    ) {
      const sorted = [...m.selections].sort(
        (a, b) => (a.columnIndex ?? 0) - (b.columnIndex ?? 0),
      );
      odds.home = sorted[0]?.price ?? null;
      odds.draw = sorted[1]?.price ?? null;
      odds.away = sorted[2]?.price ?? null;
    } else if (mType === "DBLC" && Array.isArray(m.selections)) {
      m.selections.forEach((sel) => {
        const n = (sel.name || "").toLowerCase();
        const hasHome = n.includes(odds.homeTeam.toLowerCase());
        const hasAway = n.includes(odds.awayTeam.toLowerCase());
        const hasEmpate = n.includes("empate");
        if (hasHome && hasEmpate && !hasAway) odds.dc1X = sel.price;
        else if (hasAway && hasEmpate && !hasHome) odds.dcX2 = sel.price;
        else if (hasHome && hasAway && !hasEmpate) odds.dc12 = sel.price;
      });
    } else if (mType === "BTSC" && Array.isArray(m.selections)) {
      m.selections.forEach((sel) => {
        const n = (sel.name || "").toLowerCase();
        if (n === "s\u00ed" || n === "si" || n === "yes")
          odds.bttsYes = sel.price;
        else if (n === "no") odds.bttsNo = sel.price;
      });
    } else if (mType === "HCTG") {
      extractOverUnder(
        m,
        odds.goalsLines,
        odds.goalsOverOdds,
        odds.goalsUnderOdds,
      );
    } else if (mType === "CNOU") {
      extractOverUnder(
        m,
        odds.cornersLines,
        odds.cornersOverOdds,
        odds.cornersUnderOdds,
      );
    } else if (mType === "TCOU") {
      extractOverUnder(
        m,
        odds.cardsLines,
        odds.cardsOverOdds,
        odds.cardsUnderOdds,
      );
    } else if (mType === "X002") {
      extractOverUnder(
        m,
        odds.shotsTargetLines,
        odds.shotsTargetOverOdds,
        odds.shotsTargetUnderOdds,
      );
    } else if (mType === "4159") {
      extractOverUnder(
        m,
        odds.shotsLines,
        odds.shotsOverOdds,
        odds.shotsUnderOdds,
      );
    }
  });

  function filterPaired(linesArr, overDict, underDict) {
    const paired = linesArr.filter((line) => {
      const key = line.toString();
      return overDict[key] !== undefined && underDict[key] !== undefined;
    });
    linesArr.length = 0;
    paired.forEach((l) => linesArr.push(l));
    Object.keys(overDict).forEach((k) => {
      if (!paired.map(String).includes(k)) delete overDict[k];
    });
    Object.keys(underDict).forEach((k) => {
      if (!paired.map(String).includes(k)) delete underDict[k];
    });
  }

  filterPaired(odds.goalsLines, odds.goalsOverOdds, odds.goalsUnderOdds);
  filterPaired(odds.cornersLines, odds.cornersOverOdds, odds.cornersUnderOdds);
  filterPaired(odds.cardsLines, odds.cardsOverOdds, odds.cardsUnderOdds);
  filterPaired(odds.shotsLines, odds.shotsOverOdds, odds.shotsUnderOdds);
  filterPaired(
    odds.shotsTargetLines,
    odds.shotsTargetOverOdds,
    odds.shotsTargetUnderOdds,
  );

  const MIN_CORNERS = 4.5;
  odds.cornersLines = odds.cornersLines.filter((l) => l >= MIN_CORNERS);
  Object.keys(odds.cornersOverOdds).forEach((k) => {
    if (parseFloat(k) < MIN_CORNERS) delete odds.cornersOverOdds[k];
  });
  Object.keys(odds.cornersUnderOdds).forEach((k) => {
    if (parseFloat(k) < MIN_CORNERS) delete odds.cornersUnderOdds[k];
  });

  odds.goalsLines.sort((a, b) => a - b);
  odds.cornersLines.sort((a, b) => a - b);
  odds.cardsLines.sort((a, b) => a - b);
  odds.shotsLines.sort((a, b) => a - b);
  odds.shotsTargetLines.sort((a, b) => a - b);

  return odds;
}

function buildBetanoOddsPayload(parsed) {
  return {
    bookmaker: parsed.bookmaker,
    home_team: parsed.homeTeam,
    away_team: parsed.awayTeam,
    home: parsed.home,
    draw: parsed.draw,
    away: parsed.away,
    btts_yes: parsed.bttsYes,
    btts_no: parsed.bttsNo,
    dc_1x: parsed.dc1X,
    dc_x2: parsed.dcX2,
    dc_12: parsed.dc12,
    goals_lines: parsed.goalsLines.map(String),
    goals_over: parsed.goalsOverOdds,
    goals_under: parsed.goalsUnderOdds,
    corners_lines: parsed.cornersLines.map(String),
    corners_over: parsed.cornersOverOdds,
    corners_under: parsed.cornersUnderOdds,
    cards_lines: parsed.cardsLines.map(String),
    cards_over: parsed.cardsOverOdds,
    cards_under: parsed.cardsUnderOdds,
    shots_lines: parsed.shotsLines.map(String),
    shots_over: parsed.shotsOverOdds,
    shots_under: parsed.shotsUnderOdds,
    shots_target_lines: parsed.shotsTargetLines.map(String),
    shots_target_over: parsed.shotsTargetOverOdds,
    shots_target_under: parsed.shotsTargetUnderOdds,
  };
}

// ═══════════════════════════════════════════════════════════════
// ORQUESTADOR: dado home/away, busca en Betano, trae y parsea cuotas.
// ═══════════════════════════════════════════════════════════════
async function fetchBetanoOddsForTeams(homeTeam, awayTeam, leagueName) {
  try {
    const homeVariants = getNameVariants(homeTeam);
    const awayVariants = getNameVariants(awayTeam);

    if (!homeVariants.length || !awayVariants.length) {
      return {
        success: false,
        error: "Faltan nombres de equipos para buscar en Betano",
      };
    }

    let best = null;
    const triedTerms = new Set();

    const combos = [];
    homeVariants.forEach((h) => {
      awayVariants.forEach((a) => {
        combos.push(`${h} - ${a}`);
      });
    });
    homeVariants.forEach((h) => combos.push(h));
    awayVariants.forEach((a) => combos.push(a));

    for (const term of combos) {
      if (triedTerms.has(term)) continue;
      triedTerms.add(term);
      try {
        const events = await fetchBetanoSearch(term);
        best = pickBestBetanoEvent(events, homeVariants, awayVariants);
        if (best) break;
      } catch (e) {
        console.warn(
          `[Watson] Búsqueda de Betano falló para "${term}":`,
          e.message,
        );
      }
    }

    if (!best) {
      const leagueFallbackUrl = getBetanoLeagueFallbackUrl(leagueName);
      if (leagueFallbackUrl) {
        try {
          const leagueEvents = await fetchBetanoLeagueEvents(leagueFallbackUrl);
          best = pickBestBetanoEvent(leagueEvents, homeVariants, awayVariants);
        } catch (e) {
          console.warn("[Watson] Fallback de liga de Betano falló:", e.message);
        }
      }
    }

    if (!best) {
      return {
        success: false,
        error: `No se encontró "${homeVariants[0]} vs ${awayVariants[0]}" en Betano`,
      };
    }

    const info = extractSlugIdFromEvent(best);
    if (!info) {
      return {
        success: false,
        error: "No se pudo extraer slug/id del evento de Betano",
      };
    }

    const apiUrl = `https://www.betano.co/api/cuotas-de-partido/${info.slug}/${info.id}?bt=13&req=s,stnf,c,mb,mbl`;
    const response = await fetch(apiUrl, {
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      return {
        success: false,
        error: `HTTP ${response.status} al obtener cuotas de Betano`,
      };
    }

    const betanoData = await response.json();
    let eventData =
      betanoData?.data?.event || betanoData?.data || betanoData?.event;

    if (!eventData) {
      return { success: false, error: "Respuesta de Betano sin eventData" };
    }
    if (!eventData.markets && eventData.event) {
      eventData = eventData.event;
    }

    const parsed = parseBetanoOdds(eventData);
    const payload = buildBetanoOddsPayload(parsed);

    return {
      success: true,
      bookmaker: "betano",
      homeTeam: parsed.homeTeam,
      awayTeam: parsed.awayTeam,
      matchedLabel: best.label,
      slug: info.slug,
      eventId: info.id,
      payload,
    };
  } catch (err) {
    return { success: false, error: err.message };
  }
}
