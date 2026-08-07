// betplayOdds.js - Búsqueda y parseo de cuotas de BetPlay (Kambi) sin visitar el partido
// Se carga en el Service Worker vía importScripts("betplayOdds.js")
// IMPORTANTE: debe cargarse DESPUÉS de betanoOdds.js, ya que reutiliza
// normalizeTeamName(), getNameVariants() y buildWordSet() definidas ahí.
//
// Flujo Kambi (BetPlay):
//   1) /term/search.json?term={equipo}          -> searchHitsId: ["/football/all/all/slug"]
//   2) /listView{searchHitsId}.json             -> events: [{ event: { id, homeName, awayName, ... } }]
//   3) /betoffer/event/{id}.json                -> betOffers: [...]
//
// Todas las cuotas y líneas de Kambi vienen multiplicadas por 1000.

const KAMBI_BASE =
  "https://us.offering-api.kambicdn.com/offering/v2018/betplay";

const EXCLUDED_VARIANT_PATTERN =
  /(\(w\)|\(f\)|_w_|_w$|-w$|\bw\)|femenin|women|fem\.|damas|sub-?\d{2}\b|\bu-?\d{2}\b|reserve|reservas|\bb-?team\b|_ii\b|\bii\b$|amateur|youth|juvenil|junior(es)?)/i;

function isExcludedTeamVariant(text) {
  return EXCLUDED_VARIANT_PATTERN.test(text || "");
}

async function fetchKambiSearch(term) {
  const url = `${KAMBI_BASE}/term/search.json?lang=es_CO&market=CO&client_id=200&channel_id=3&term=${encodeURIComponent(term)}`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} en búsqueda de BetPlay`);
  }
  const json = await response.json();
  return {
    hits: json?.searchHitsId || [],
    terms: json?.resultTerms || [],
  };
}

function rankAndFilterHits(hits, terms) {
  const labelById = {};
  (terms || []).forEach((t) => {
    if (t.type === "PARTICIPANT" && t.id) {
      labelById[t.id] = `${t.localizedName || ""} ${t.englishName || ""}`;
    }
  });

  const clean = hits.filter(
    (hitPath) => !isExcludedTeamVariant(labelById[hitPath] || hitPath),
  );

  return clean.length > 0 ? clean : hits;
}

async function fetchKambiListView(hitPath) {
  const url = `${KAMBI_BASE}/listView${hitPath}.json?channel_id=3&client_id=200&lang=es_CO&market=CO`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} en listView de BetPlay`);
  }
  const json = await response.json();
  return json?.events || [];
}

async function fetchKambiBetOffers(eventId) {
  const url = `${KAMBI_BASE}/betoffer/event/${eventId}.json?channel_id=3&client_id=200&lang=es_CO&market=CO`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} en betoffer de BetPlay`);
  }
  const json = await response.json();
  return json?.betOffers || [];
}

/**
 * Elige el mejor evento de Kambi/BetPlay dado un listado de /listView.
 *
 * FIX CLAVE: cuando dos equipos distintos comparten el mismo nombre base
 * (ej. "Universidad Católica" de Chile y Ecuador), el hit de búsqueda
 * equivocado puede devolver un listView cuyo partido NO tiene nada que ver
 * con tu equipo local (ej. "Libertad Loja - Universidad Católica (ECU)").
 * Antes, si 2+ palabras del NOMBRE DEL RIVAL (mismo lado) matcheaban, el
 * score llegaba al umbral y se aceptaba igual, aunque el equipo local no
 * matcheara nada. Ahora se exige homeHit === true Y awayHit === true; si
 * no, se descarta el evento y fetchBetPlayOddsForTeams sigue probando el
 * siguiente hit (la variante correcta, ej. "...__chi_").
 */
function pickBestKambiEvent(events, homeVariants, awayVariants) {
  const homeWords = buildWordSet(homeVariants);
  const awayWords = buildWordSet(awayVariants);

  let best = null;
  let bestScore = 0;

  (events || []).forEach((wrap) => {
    const ev = wrap.event || wrap;
    const rawLabel = `${ev.homeName || ""} ${ev.awayName || ""}`;
    const groupLabel = `${ev.group || ""} ${ev.tournament?.name || ""}`;

    if (isExcludedTeamVariant(rawLabel) || isExcludedTeamVariant(groupLabel)) {
      return;
    }

    const label = normalizeTeamName(rawLabel);
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
    // Esto es lo que resuelve la ambigüedad "Universidad Católica CHI vs ECU":
    // el listView equivocado (rival real = Libertad Loja) nunca tendrá homeHit,
    // así que se descarta y se prueba el siguiente hit de búsqueda.
    if (!homeHit || !awayHit) return;

    score += 2; // bonus por matchear ambos lados

    if (score > bestScore) {
      bestScore = score;
      best = ev;
    }
  });

  return best;
}

function isTeamSpecificCriterion(criterion) {
  const label = (criterion.label || "").toLowerCase();
  const eLabel = (criterion.englishLabel || "").toLowerCase();
  return (
    label.includes(" a favor de ") ||
    eLabel.includes(" by ") ||
    eLabel.startsWith("most ") ||
    label.startsWith("más ") ||
    label.startsWith("mas ")
  );
}

function parseBetPlayOdds(betOffers, homeTeamName, awayTeamName) {
  const odds = {
    bookmaker: "betplay",
    homeTeam: homeTeamName || "Local",
    awayTeam: awayTeamName || "Visitante",
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
    handicapLines: [],
    handicapHomeOdds: {},
    handicapAwayOdds: {},
  };

  const addOverUnder = (offer, linesArr, overDict, underDict) => {
    (offer.outcomes || []).forEach((oc) => {
      if (oc.status !== "OPEN" || oc.odds == null || oc.line == null) return;
      const line = oc.line / 1000;
      const price = oc.odds / 1000;
      if (price < 1.01) return;

      const key = line.toString();
      if (!linesArr.includes(line)) linesArr.push(line);

      if (oc.type === "OT_OVER") overDict[key] = price;
      else if (oc.type === "OT_UNDER") underDict[key] = price;
    });
  };

  (betOffers || []).forEach((offer) => {
    const criterion = offer.criterion || {};
    const label = (criterion.label || "").toLowerCase();
    const eLabel = (criterion.englishLabel || "").toLowerCase();
    const typeId = offer.betOfferType?.id;

    if (
      typeId === 2 &&
      (eLabel === "full time" || label === "resultado final")
    ) {
      (offer.outcomes || []).forEach((oc) => {
        if (oc.status !== "OPEN" || oc.odds == null) return;
        const price = oc.odds / 1000;
        if (oc.type === "OT_ONE") odds.home = price;
        else if (oc.type === "OT_CROSS") odds.draw = price;
        else if (oc.type === "OT_TWO") odds.away = price;
      });
      return;
    }

    if (eLabel.trim() === "Double Chance") {
      (offer.outcomes || []).forEach((oc) => {
        if (oc.status !== "OPEN" || oc.odds == null) return;
        const price = oc.odds / 1000;
        if (oc.type === "OT_ONE_OR_CROSS") odds.dc1X = price;
        else if (oc.type === "OT_ONE_OR_TWO") odds.dc12 = price;
        else if (oc.type === "OT_CROSS_OR_TWO") odds.dcX2 = price;
      });
      return;
    }

    if (eLabel.trim() === "Both Teams To Score") {
      (offer.outcomes || []).forEach((oc) => {
        if (oc.status !== "OPEN" || oc.odds == null) return;
        const price = oc.odds / 1000;
        if (oc.type === "OT_YES") odds.bttsYes = price;
        else if (oc.type === "OT_NO") odds.bttsNo = price;
      });
      return;
    }

    if (typeId !== 6) return;
    if (isTeamSpecificCriterion(criterion)) return;

    if (eLabel.trim() === "total goals") {
      addOverUnder(
        offer,
        odds.goalsLines,
        odds.goalsOverOdds,
        odds.goalsUnderOdds,
      );
    } else if (eLabel.trim() === "total cards") {
      addOverUnder(
        offer,
        odds.cardsLines,
        odds.cardsOverOdds,
        odds.cardsUnderOdds,
      );
    } else if (eLabel.trim() === "total shots on target") {
      addOverUnder(
        offer,
        odds.shotsTargetLines,
        odds.shotsTargetOverOdds,
        odds.shotsTargetUnderOdds,
      );
    } else if (eLabel.trim() === "total shots") {
      addOverUnder(
        offer,
        odds.shotsLines,
        odds.shotsOverOdds,
        odds.shotsUnderOdds,
      );
    } else if (eLabel.trim() === "total corners") {
      addOverUnder(
        offer,
        odds.cornersLines,
        odds.cornersOverOdds,
        odds.cornersUnderOdds,
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

  [
    odds.goalsLines,
    odds.cornersLines,
    odds.cardsLines,
    odds.shotsLines,
    odds.shotsTargetLines,
  ].forEach((arr) => arr.sort((a, b) => a - b));

  return odds;
}

function buildBetPlayOddsPayload(parsed) {
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

/**
 * Orquestador: dado home/away, busca en BetPlay, trae y parsea cuotas.
 *
 * homeTeam/awayTeam pueden ser string u objeto { name, shortName }.
 * Prueba TODOS los hits filtrados (no solo los primeros 3) porque con
 * nombres ambiguos (Universidad Católica CHI/ECU, River Plate ARG/URU/COL,
 * etc.) el hit correcto puede venir en cualquier posición, y ahora que
 * pickBestKambiEvent exige match en ambos lados, los hits incorrectos se
 * descartan solos sin producir falsos positivos.
 */
async function fetchBetPlayOddsForTeams(homeTeam, awayTeam) {
  try {
    const homeVariants = getNameVariants(homeTeam);
    const awayVariants = getNameVariants(awayTeam);

    if (!homeVariants.length || !awayVariants.length) {
      return {
        success: false,
        error: "Faltan nombres de equipos para buscar en BetPlay",
      };
    }

    const searchTerms = [...homeVariants, ...awayVariants];
    let filteredHits = [];

    for (const term of searchTerms) {
      try {
        const { hits, terms } = await fetchKambiSearch(term);
        if (hits.length) {
          const filtered = rankAndFilterHits(hits, terms);
          if (filtered.length) {
            filteredHits = filtered;
            break;
          }
        }
      } catch (e) {
        console.warn(
          `[Watson] Búsqueda de BetPlay falló para "${term}":`,
          e.message,
        );
      }
    }

    if (!filteredHits.length) {
      return {
        success: false,
        error: `No se encontró "${homeVariants[0]}" en BetPlay`,
      };
    }

    // Probar TODOS los hits filtrados (hasta un tope razonable) hasta
    // encontrar uno cuyo listView tenga un evento que matchee AMBOS equipos.
    let matchedEvent = null;
    for (const hitPath of filteredHits.slice(0, 8)) {
      try {
        const events = await fetchKambiListView(hitPath);
        const best = pickBestKambiEvent(events, homeVariants, awayVariants);
        if (best) {
          matchedEvent = best;
          break;
        }
      } catch (e) {
        console.warn(
          "[Watson] listView BetPlay falló para",
          hitPath,
          e.message,
        );
      }
    }

    if (!matchedEvent) {
      return {
        success: false,
        error: `No se encontró "${homeVariants[0]} vs ${awayVariants[0]}" en BetPlay`,
      };
    }

    const betOffers = await fetchKambiBetOffers(matchedEvent.id);
    if (!betOffers.length) {
      return {
        success: false,
        error: "BetPlay no devolvió mercados para este partido",
      };
    }

    const parsed = parseBetPlayOdds(
      betOffers,
      matchedEvent.homeName || homeVariants[0],
      matchedEvent.awayName || awayVariants[0],
    );
    const payload = buildBetPlayOddsPayload(parsed);

    return {
      success: true,
      bookmaker: "betplay",
      homeTeam: parsed.homeTeam,
      awayTeam: parsed.awayTeam,
      matchedLabel: matchedEvent.name,
      eventId: matchedEvent.id,
      payload,
    };
  } catch (err) {
    return { success: false, error: err.message };
  }
}
