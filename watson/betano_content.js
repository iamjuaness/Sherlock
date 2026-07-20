// betano_content.js - Script de contenido para Betano
(function () {
  let lastUrl = location.href;

  function extractMatchInfo(url) {
    const match = url.match(/\/cuotas-de-partido\/([^\/]+)\/(\d+)/);
    if (match) {
      return { slug: match[1], id: match[2] };
    }
    return null;
  }

  // ──────────────────────────────────────────────────────────────
  // parseBetanoOdds
  // Recibe el objeto "event" devuelto por la API de Betano.
  // Devuelve un objeto con la misma estructura que FootballOdds de Sherlock.
  // ──────────────────────────────────────────────────────────────
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
      dnbHome: null,
      dnbAway: null,

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

    // Extraer nombres de equipos del nombre del evento
    const nameParts = (eventData.name || eventData.shortName || "")
      .split(" - ")
      .map((s) => s.trim());
    odds.homeTeam = nameParts[0] || "Local";
    odds.awayTeam = nameParts[1] || "Visitante";

    // ── Helper: Over/Under ───────────────────────────────────────
    // Regla Betano: columnIndex === 0 → over  |  columnIndex === 1 → under
    // Cada selection lleva su propia línea en sel.handicap.
    const extractOverUnder = (market, linesArr, overDict, underDict) => {
      if (!Array.isArray(market.selections) || market.selections.length === 0)
        return;

      market.selections.forEach((sel) => {
        // Línea: siempre en sel.handicap
        const line =
          sel.handicap !== undefined && sel.handicap !== null
            ? Number(sel.handicap)
            : null;

        if (!line || line === 0) return;

        // Solo enviar líneas que sean .5 (e.g. 0.5, 1.5, etc.)
        if (Math.abs((line % 1) - 0.5) > 0.001) return;

        const key = line.toString();
        if (!linesArr.includes(line)) linesArr.push(line);

        // columnIndex 0 = over, columnIndex 1 = under
        if (sel.columnIndex === 0) overDict[key] = sel.price;
        else if (sel.columnIndex === 1) underDict[key] = sel.price;
      });
    };
    // ── Helper: Draw No Bet (DNOB) ─────────────────────────────
    // ── Helper: Hándicap (FHMR / FHH1) ─────────────────────────
    const extractHandicap = (market, linesArr, homeDict, awayDict) => {
      const homeL = odds.homeTeam.toLowerCase();
      const awayL = odds.awayTeam.toLowerCase();

      const processRow = (selections, line) => {
        if (!Array.isArray(selections)) return;
        selections.forEach((sel) => {
          const n = (sel.name || "").toLowerCase();
          const s = (sel.shortName || "").toLowerCase();
          const strLine = line !== null ? String(line) : null;
          if (!strLine) return;
          if (!linesArr.includes(line)) linesArr.push(line);
          const isHome = s === "1" || n.includes(homeL) || n.includes("local");
          const isAway =
            s === "2" || n.includes(awayL) || n.includes("visitante");
          if (isHome && !n.includes("empate")) homeDict[strLine] = sel.price;
          else if (isAway && !n.includes("empate"))
            awayDict[strLine] = sel.price;
        });
      };

      if (market.tableLayout && Array.isArray(market.tableLayout.rows)) {
        market.tableLayout.rows.forEach((row) => {
          const gs = row.groupSelections && row.groupSelections[0];
          if (!gs) return;
          let line = gs.handicap != null ? Number(gs.handicap) : null;
          if (line === null && row.title) {
            const m = row.title.match(/([+-]?\d+\.?\d*)/);
            if (m) line = parseFloat(m[1]);
          }
          processRow(gs.selections, line);
        });
      } else if (Array.isArray(market.selections)) {
        const line = market.handicap != null ? Number(market.handicap) : null;
        processRow(market.selections, line);
      }
    };

    // ── Iterar mercados ──────────────────────────────────────────
    eventData.markets.forEach((m) => {
      const mType = (m.type || "").toUpperCase();
      const mName = (m.name || "").toLowerCase();

      // ── 1X2 ──
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
      }

      // ── Doble Oportunidad ──
      else if (mType === "DBLC" && Array.isArray(m.selections)) {
        m.selections.forEach((sel) => {
          const n = (sel.name || "").toLowerCase();
          // Betano: "Guayaquil City FC o Empate" / "Delfín SC o Empate" / "Guayaquil City FC o Delfín SC"
          const hasHome = n.includes(odds.homeTeam.toLowerCase());
          const hasAway = n.includes(odds.awayTeam.toLowerCase());
          const hasEmpate = n.includes("empate");

          if (hasHome && hasEmpate && !hasAway) odds.dc1X = sel.price;
          else if (hasAway && hasEmpate && !hasHome) odds.dcX2 = sel.price;
          else if (hasHome && hasAway && !hasEmpate) odds.dc12 = sel.price;
        });
      }

      // ── Ambos anotan ──
      else if (mType === "BTSC" && Array.isArray(m.selections)) {
        m.selections.forEach((sel) => {
          const n = (sel.name || "").toLowerCase();
          if (n === "s\u00ed" || n === "si" || n === "yes")
            odds.bttsYes = sel.price;
          else if (n === "no") odds.bttsNo = sel.price;
        });
      }

      // ── Goles Totales Más/Menos (HCTG) ──
      else if (
        mType === "HCTG" ||
        (mName.includes("goles") &&
          (mName.includes("m\u00e1s/menos") || mName.includes("mas/menos")) &&
          !mName.includes("primer tiempo") &&
          !mName.includes("segundo tiempo") &&
          !mName.includes("equipo"))
      ) {
        extractOverUnder(
          m,
          odds.goalsLines,
          odds.goalsOverOdds,
          odds.goalsUnderOdds,
        );
      }

      // ── Tiros de Esquina (CNOU) ──
      else if (
        mType === "CNOU" ||
        (mName.includes("esquina") &&
          (mName.includes("m\u00e1s/menos") || mName.includes("mas/menos")) &&
          !mName.includes("primer") &&
          !mName.includes("segundo"))
      ) {
        extractOverUnder(
          m,
          odds.cornersLines,
          odds.cornersOverOdds,
          odds.cornersUnderOdds,
        );
      }

      // ── Tarjetas ──
      else if (
        mName.includes("tarjeta") &&
        (mName.includes("m\u00e1s/menos") ||
          mName.includes("mas/menos") ||
          mName.includes("total"))
      ) {
        extractOverUnder(
          m,
          odds.cardsLines,
          odds.cardsOverOdds,
          odds.cardsUnderOdds,
        );
      }

      // ── Tiros al Arco / Tiros a Puerta ──
      else if (
        mType === "X002" ||
        (mName.includes("tiros") &&
          (mName.includes("puerta") || mName.includes("arco")) &&
          (mName.includes("m\u00e1s/menos") || mName.includes("mas/menos")))
      ) {
        extractOverUnder(
          m,
          odds.shotsTargetLines,
          odds.shotsTargetOverOdds,
          odds.shotsTargetUnderOdds,
        );
      }

      // ── Tiros (generales) / Remates totales ──
      else if (
        mType === "4159" ||
        (mName.includes("remates") && mName.includes("totales")) ||
        (mName.includes("tiros") &&
          !mName.includes("puerta") &&
          !mName.includes("arco") &&
          !mName.includes("esquina") &&
          (mName.includes("m\u00e1s/menos") || mName.includes("mas/menos")))
      ) {
        extractOverUnder(
          m,
          odds.shotsLines,
          odds.shotsOverOdds,
          odds.shotsUnderOdds,
        );
      }

      // ── Draw No Bet / Apuesta sin Empate (DNOB) ──
      else if (
        mType === "DNOB" ||
        mName.includes("sin empate") ||
        mName.includes("draw no bet")
      ) {
        if (Array.isArray(m.selections)) {
          m.selections.forEach((sel) => {
            // columnIndex 0 = Local, columnIndex 1 = Visitante
            if (sel.columnIndex === 0) odds.dnbHome = sel.price;
            else if (sel.columnIndex === 1) odds.dnbAway = sel.price;
          });
        }
      }

      // ── Hándicap ──
      else if (
        mType === "FHMR" ||
        mType === "AHRF" ||
        mType === "FHH1" ||
        mName.includes("h\u00e1ndicap") ||
        mName.includes("handicap")
      ) {
        extractHandicap(
          m,
          odds.handicapLines,
          odds.handicapHomeOdds,
          odds.handicapAwayOdds,
        );
      }
    });

    // ── Eliminar líneas O/U sin contraparte ─────────────────────
    // Si una línea tiene over pero no under (o viceversa), se descarta.
    function filterPaired(linesArr, overDict, underDict) {
      const paired = linesArr.filter((line) => {
        const key = line.toString();
        return overDict[key] !== undefined && underDict[key] !== undefined;
      });
      // Eliminar entradas huérfanas de los diccionarios
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
    filterPaired(
      odds.cornersLines,
      odds.cornersOverOdds,
      odds.cornersUnderOdds,
    );
    filterPaired(odds.cardsLines, odds.cardsOverOdds, odds.cardsUnderOdds);
    filterPaired(odds.shotsLines, odds.shotsOverOdds, odds.shotsUnderOdds);
    filterPaired(
      odds.shotsTargetLines,
      odds.shotsTargetOverOdds,
      odds.shotsTargetUnderOdds,
    );

    // Descartar líneas de corners < 4.5 (líneas muy bajas no son útiles)
    const MIN_CORNERS = 4.5;
    odds.cornersLines = odds.cornersLines.filter((l) => l >= MIN_CORNERS);
    Object.keys(odds.cornersOverOdds).forEach((k) => {
      if (parseFloat(k) < MIN_CORNERS) delete odds.cornersOverOdds[k];
    });
    Object.keys(odds.cornersUnderOdds).forEach((k) => {
      if (parseFloat(k) < MIN_CORNERS) delete odds.cornersUnderOdds[k];
    });

    // Ordenar líneas
    odds.goalsLines.sort((a, b) => a - b);
    odds.cornersLines.sort((a, b) => a - b);
    odds.cardsLines.sort((a, b) => a - b);
    odds.shotsLines.sort((a, b) => a - b);
    odds.shotsTargetLines.sort((a, b) => a - b);
    odds.handicapLines.sort((a, b) => a - b);

    return odds;
  }

  // ── Mapeo al formato que espera el endpoint /api/v1/prefill/odds ─
  // Usa snake_case coincidente con FootballOdds de Sherlock.
  // El backend normaliza: goals_over → goalsOverOdds (camelCase) para el comparador.
  function buildSherlockPayload(parsed) {
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
      dnb_home: parsed.dnbHome,
      dnb_away: parsed.dnbAway,
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
      handicap_lines: parsed.handicapLines.map(String),
      handicap_home: parsed.handicapHomeOdds,
      handicap_away: parsed.handicapAwayOdds,
    };
  }

  // ── Fetch principal ──────────────────────────────────────────────
  async function fetchAndSendOdds(matchInfo) {
    const apiUrl = `https://www.betano.co/api/cuotas-de-partido/${matchInfo.slug}/${matchInfo.id}?bt=13&req=s,stnf,c,mb,mbl`;

    try {
      const response = await fetch(apiUrl, {
        headers: { Accept: "application/json" },
      });

      if (!response.ok) {
        console.error(
          "[Watson] Error HTTP al obtener cuotas:",
          response.status,
        );
        return;
      }

      const betanoData = await response.json();

      // La API devuelve: { data: { event: { ... } } }
      // Probar ambos paths por si cambia la estructura
      let eventData =
        betanoData?.data?.event || // path esperado
        betanoData?.data || // fallback: data ES el evento
        betanoData?.event; // fallback: raíz tiene event

      if (!eventData) {
        console.error(
          "[Watson] No se encontró eventData en la respuesta:",
          betanoData,
        );
        return;
      }

      // Si eventData no tiene markets pero tiene event, bajar un nivel más
      if (!eventData.markets && eventData.event) {
        eventData = eventData.event;
      }

      const parsedOdds = parseBetanoOdds(eventData);
      const payload = { odds: buildSherlockPayload(parsedOdds) };

      // Leer endpoint configurado en la extensión (o usar default)
      const stored = await chrome.storage.sync.get(["endpointUrl"]);
      const base = (stored.endpointUrl || "http://localhost:8000").replace(
        /\/+$/,
        "",
      );
      const sherlockUrl = `${base}/odds`;

      const sherlockResponse = await fetch(sherlockUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (sherlockResponse.ok) {
        console.log("[Watson] ✅");
      } else {
        console.error(
          "[Watson] ❌ Error enviando a Sherlock:",
          sherlockResponse.status,
        );
      }

      // Guardar en chrome.storage.local para que el popup lo pueda enviar manualmente
      const betanoStorage = {
        url: location.href,
        timestamp: new Date().toISOString(),
        payload: payload,
        homeTeam: parsedOdds.homeTeam,
        awayTeam: parsedOdds.awayTeam,
      };
      await chrome.storage.local.set({ lastBetanoOdds: betanoStorage });

      // Notificar al popup para que actualice la vista si está abierto
      try {
        chrome.runtime.sendMessage({
          action: "betanoOddsCaptured",
          data: betanoStorage,
        });
      } catch (_) {
        // Ignorar si el popup está cerrado
      }
    } catch (err) {
      console.error("[Watson] ❌ Excepción:", err);
    }
  }

  // ── Detección de URL ─────────────────────────────────────────────
  let timeoutId = null;
  function checkCurrentUrl() {
    if (timeoutId) clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
      const matchInfo = extractMatchInfo(location.href);
      if (matchInfo) fetchAndSendOdds(matchInfo);
    }, 1200);
  }

  checkCurrentUrl();

  new MutationObserver(() => {
    const url = location.href;
    if (url !== lastUrl) {
      lastUrl = url;
      checkCurrentUrl();
    }
  }).observe(document, { subtree: true, childList: true });
})();
