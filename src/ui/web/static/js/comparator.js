/* ═══════════════════════════════════════════════════════════════
   Sherlock v0.5 – Comparator Engine (Frontend)
   ═══════════════════════════════════════════════════════════════ */
function renderMarkdown(text) {
  return (
    text
      // Escape HTML primero (seguridad)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")

      // Bloques de código ```
      .replace(/```[\w]*\n?([\s\S]*?)```/g, "<pre><code>$1</code></pre>")

      // Headers ### ## #
      .replace(/^### (.+)$/gm, "<h3>$1</h3>")
      .replace(/^## (.+)$/gm, "<h2>$1</h2>")
      .replace(/^# (.+)$/gm, "<h1>$1</h1>")

      // Negrita **texto** y __texto__
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/__(.+?)__/g, "<strong>$1</strong>")

      // Cursiva *texto* y _texto_
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/_(.+?)_/g, "<em>$1</em>")

      // Código inline `código`
      .replace(/`(.+?)`/g, "<code>$1</code>")

      // Listas con viñetas - item o * item
      .replace(/^[\-\*] (.+)$/gm, "<li>$1</li>")
      .replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>")

      // Listas numeradas 1. item
      .replace(/^\d+\. (.+)$/gm, "<li>$1</li>")

      // Líneas separadoras ---
      .replace(/^---+$/gm, "<hr>")

      // Saltos de línea dobles → párrafos
      .replace(/\n\n+/g, "</p><p>")

      // Wrap en párrafo
      .replace(/^(?!<[hupoli\/<])(.*)/gm, (m) => (m.trim() ? m : ""))
      .trim()
  );
}

// ── Tab switching ────────────────────────────────────────────────
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document
      .querySelectorAll(".tab")
      .forEach((t) => t.classList.remove("tab--active"));
    document
      .querySelectorAll(".panel")
      .forEach((p) => p.classList.remove("panel--active"));
    tab.classList.add("tab--active");
    document
      .getElementById(`panel-${tab.dataset.sport}`)
      .classList.add("panel--active");
    document.getElementById("results").style.display = "none";

    // Update active sport for history filtering
    const historySport = document.getElementById("history-sport");
    if (historySport) historySport.value = tab.dataset.sport;
  });
});

const sherlockBtn = document.getElementById("btn-sherlock-analysis");
if (sherlockBtn) {
  sherlockBtn.addEventListener("click", requestSherlockAnalysis);
}

let currentSport = "football";
let currentPayload = null;
let radarChart = null;
let barChart = null;
let probChart = null;
let currentResults = null;
let loadedHistoryEntryId = null;
let loadedHistoryEntryDate = null;

// ── Prefill polling (for browser extension integration) ─────────
(function startPrefillPolling() {
  const POLL_INTERVAL = 2500; // ms
  let _prefillTimer = null;

  async function checkPrefill() {
    try {
      const res = await fetch("/api/v1/prefill");
      if (!res.ok) return;
      const data = await res.json();
      if (data.pending && data.payload) {
        const payload = data.payload;
        const sport = payload.sport || "football";

        // Show notification banner
        showPrefillBanner(sport, payload);

        // Fill in the form
        populateAppForm(sport, payload);
      }
    } catch (_) {
      /* silently ignore network errors */
    }
    _prefillTimer = setTimeout(checkPrefill, POLL_INTERVAL);
  }

  function showPrefillBanner(sport, payload) {
    let existing = document.getElementById("prefill-toast");
    if (existing) existing.remove();

    const home = payload?.home?.name || "";
    const away = payload?.away?.name || "";
    const banner = document.createElement("div");
    banner.id = "prefill-toast";
    banner.style.cssText = `
      position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 9999;
      background: linear-gradient(135deg, #10b981, #059669);
      color: #fff; padding: 0.9rem 1.4rem; border-radius: 12px;
      box-shadow: 0 8px 32px rgba(16,185,129,0.35);
      font-size: 0.9rem; font-weight: 600; display: flex; align-items: center; gap: 0.75rem;
      animation: slideInRight 0.35s ease;
    `;
    banner.innerHTML = `
      <span style="font-size:1.4rem">📥</span>
      <div>
        <div>Datos cargados desde extensión</div>
        ${home && away ? `<div style="font-size:0.78rem; font-weight:400; opacity:0.9; margin-top:2px">${home} vs ${away}</div>` : ""}
      </div>
      <button onclick="this.parentElement.remove()" style="background:none;border:none;color:#fff;font-size:1.1rem;cursor:pointer;margin-left:0.5rem;">✕</button>
    `;
    document.body.appendChild(banner);
    setTimeout(() => banner && banner.remove(), 6000);
  }

  _prefillTimer = setTimeout(checkPrefill, 1500);
})();

// ── Helpers ──────────────────────────────────────────────────────
function val(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  if (el.type === "number") {
    const v = parseFloat(el.value);
    return isNaN(v) ? 0 : v;
  }
  return el.value.trim();
}

function toNullableNumber(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  const raw = el.value;
  if (raw === "" || raw === null || raw === undefined) return null;
  const v = parseFloat(raw);
  return isNaN(v) ? null : v;
}

function showError(msg) {
  alert("⚠️ " + msg);
}

function renderMultiLineCards(values) {
  const grid = document.getElementById("multi-line-grid");
  const card = document.getElementById("multi-line-card");
  const underdogGrid = document.getElementById("underdog-grid");
  const underdogCard = document.getElementById("underdog-card");
  const hcGrid = document.getElementById("high-confidence-grid");
  const hcCard = document.getElementById("high-confidence-card");

  if (grid) grid.innerHTML = "";
  if (underdogGrid) underdogGrid.innerHTML = "";
  if (hcGrid) hcGrid.innerHTML = "";

  if (!Array.isArray(values)) {
    if (card) card.style.display = "none";
    if (underdogCard) underdogCard.style.display = "none";
    if (hcCard) hcCard.style.display = "none";
    return;
  }

  // ── 1. Evaluar picks (Sincronizado con Backend) ──
  const valuePicks = values
    .filter((v) => v.selection && v.odds != null)
    .filter((v) => v.is_value === true && v.is_underdog !== true) // Profesional
    .sort((a, b) => {
      const dqA = a.data_quality_score ?? 0;
      const dqB = b.data_quality_score ?? 0;
      if (dqB !== dqA) return dqB - dqA;
      return (b.model_prob ?? 0) - (a.model_prob ?? 0);
    });

  const underdogPicks = values
    .filter((v) => v.selection && v.odds != null)
    .filter((v) => v.is_underdog === true)
    .sort((a, b) => {
      const dqA = a.data_quality_score ?? 0;
      const dqB = b.data_quality_score ?? 0;
      if (dqB !== dqA) return dqB - dqA;
      return (b.model_prob ?? 0) - (a.model_prob ?? 0);
    });

  const hcPicks = values
    .filter((v) => v.selection && v.odds != null)
    .filter((v) => v.is_high_confidence === true)
    .sort((a, b) => (b.model_prob ?? 0) - (a.model_prob ?? 0));

  // Control de visibilidad
  if (card) card.style.display = valuePicks.length > 0 ? "block" : "none";
  if (underdogCard)
    underdogCard.style.display = underdogPicks.length > 0 ? "block" : "none";
  if (hcCard) hcCard.style.display = hcPicks.length > 0 ? "block" : "none";

  // Función auxiliar de renderizado de item
  const renderItem = (v, targetGrid) => {
    const edgeVal = Number(v.edge ?? 0);
    const probText = Number(v.model_prob ?? 0).toFixed(1) + "%";
    const oddsText = Number(v.odds).toFixed(2);
    const edgeText =
      edgeVal >= 0 ? `+${edgeVal.toFixed(1)}%` : `${edgeVal.toFixed(1)}%`;

    let mod = "neutral";
    let badgeText = "";

    if (v.is_publishable) {
      mod = "strong";
      badgeText = "🎯 PROFESIONAL";
    } else if (v.is_underdog) {
      mod = "underdog";
      badgeText = "🦄 UNDERDOG";
    } else if (v.is_high_confidence) {
      mod = "high"; // Use new high style
      badgeText = "⭐ ALTA CONF.";
    } else if (v.is_value) {
      mod = "value";
      badgeText = "⚖️ VALOR";
    }

    const dqScore =
      v.data_quality_score != null ? Math.round(v.data_quality_score) : null;
    const confTier = v.market_confidence_tier || "N/A";

    // Success indicator
    let successHtml = "";
    let statusClass = "";
    if (v.success === true) {
      successHtml = '<div class="value-line-card__success-marker">✅</div>';
      statusClass = "value-line-card--success";
    } else if (v.success === false) {
      successHtml = '<div class="value-line-card__success-marker">❌</div>';
      statusClass = "value-line-card--fail";
    } else if (v.success === "void") {
      successHtml =
        '<div class="value-line-card__success-marker" style="background: var(--void-bg, rgba(100,116,139,0.25)); color: #94a3b8; border: 1px solid rgba(148,163,184,0.3);">↩️</div>';
      statusClass = "value-line-card--void";
    }

    const el = document.createElement("div");
    el.className = `value-line-card value-line-card--${mod} ${statusClass}`;
    el.innerHTML = `
      ${successHtml}
      <div class="value-line-card__market" title="${v.selection}">
        ${v.selection}
      </div>
      <div class="value-line-card__row">
        <span>Confianza Datos</span>
        <span style="color: ${dqScore > 70 ? "var(--color-success)" : dqScore > 40 ? "var(--color-warning)" : "var(--color-error)"}">${dqScore ?? "—"}% (${confTier})</span>
      </div>
      <div class="value-line-card__row">
        <span>Prob. Modelo</span>
        <span>${probText}</span>
      </div>
      <div class="value-line-card__row">
        <span>Cuota Bookie</span>
        <span>${oddsText}</span>
      </div>
      <div class="value-line-card__edge" style="font-weight: bold; font-size: 1.1rem; margin-top: 0.5rem;">
        Edge ${edgeText}
      </div>
      <span class="value-line-card__badge badge--${mod}">${badgeText}</span>
    `;
    targetGrid.appendChild(el);
  };

  valuePicks.forEach((v) => renderItem(v, grid));
  underdogPicks.forEach((v) => renderItem(v, underdogGrid));
  hcPicks.forEach((v) => renderItem(v, hcGrid));
}

function renderResults(data) {
  const searchingEl = document.getElementById("searching-step");
  if (searchingEl) searchingEl.style.display = "none";

  const resultsEl = document.getElementById("results");
  if (resultsEl) {
    resultsEl.style.display = "block";
    resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  currentResults = data;

  try {
    populateMarketOptions(data);
  } catch (e) {
    console.error("renderResults error:", e);
  }

  const summaryEl = document.getElementById("results-summary");
  if (summaryEl && data.summary) {
    summaryEl.innerHTML = `<div class="summary-box">${data.summary.replace(/\n/g, "<br>")}</div>`;
  }

  try {
    if (data.values) renderMultiLineCards(data.values);
  } catch (e) {
    console.error("Error pintando tabla:", e);
  }

  try {
    const projectedLinesEl = document.getElementById("projected-lines");
    if (projectedLinesEl) {
      if (data.projected_lines && data.projected_lines.length > 0) {
        if (projectedLinesEl.parentElement)
          projectedLinesEl.parentElement.style.display = "block";

        // Custom rendering for a "premium" feel: grouping by category or showing prominent team lines
        const teamLines = [];
        const totalLines = [];

        data.projected_lines.forEach((p) => {
          if (
            p.label.includes("(") &&
            (p.label.includes(data.home_name) ||
              p.label.includes(data.away_name))
          ) {
            teamLines.push(p);
          } else {
            totalLines.push(p);
          }
        });

        const renderCard = (p) => {
          let successClass = "";
          let successMarker = "";
          if (p.success === true) {
            successClass = "projected-card--success";
            successMarker =
              '<div class="projected-card__success-marker">✅</div>';
          } else if (p.success === false) {
            successClass = "projected-card--fail";
            successMarker =
              '<div class="projected-card__success-marker">❌</div>';
          }

          let displayVal = p.value.toFixed(2);
          let extraLabel = "";

          if (
            p.type === "handicap_prob" &&
            p.prob !== null &&
            p.prob !== undefined
          ) {
            displayVal = `${p.prob}%`;
            extraLabel = `<div style="font-size: 0.7rem; opacity: 0.8; margin-top: 0.1rem;">Línea: ${p.value >= 0 ? "+" : ""}${p.value.toFixed(2)}</div>`;
          } else if (
            p.type === "double_chance" ||
            p.type === "btts" ||
            (p.type === "goals" && p.label.toLowerCase().includes("over"))
          ) {
            displayVal = `${p.value.toFixed(1)}%`;
          }

          let resultText = "";
          if (p.actual_val !== undefined && p.actual_val !== null) {
            const sign = p.diff_sign ? ` (${p.diff_sign})` : "";
            resultText = `<div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 0.25rem;">Real: ${p.actual_val}${sign}</div>`;
          }

          return `
            <div class="projected-card ${successClass}" style="position: relative; display: flex; flex-direction: column; justify-content: space-between; min-height: 90px; padding: 0.75rem 0.5rem;">
              ${successMarker}
              <div class="projected-card__label" style="margin-bottom: 0.25rem;">${p.label}</div>
              <div>
                <div class="projected-card__value" style="font-size: 1.25rem; font-weight: 700; color: var(--accent);">${displayVal}</div>
                ${extraLabel}
              </div>
              ${resultText}
            </div>
          `;
        };

        projectedLinesEl.innerHTML = `
          <div style="grid-column: 1 / -1; margin-bottom: 0.5rem; color: var(--text-secondary); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px;">Proyecciones Totales</div>
          ${totalLines.map(renderCard).join("")}
        `;
      } else {
        if (projectedLinesEl.parentElement)
          projectedLinesEl.parentElement.style.display = "none";
      }
    }
  } catch (e) {
    console.error("renderResults error:", e);
  }

  // ==========================================
  // 1. MATRIZ DE ESTADÍSTICAS (Con Barras)
  // ==========================================
  try {
    const statsTableBody = data.comparisons
      .map((c) => {
        const icon =
          c.advantage === "home" ? "🔹" : c.advantage === "away" ? "🔸" : "⚖️";
        const cls =
          c.advantage === "home"
            ? "advantage-home"
            : c.advantage === "away"
              ? "advantage-away"
              : "";

        const max = Math.max(c.homevalue, c.awayvalue) || 1;
        const homePct = (c.homevalue / max) * 100;
        const awayPct = (c.awayvalue / max) * 100;

        return `<tr class="${cls}">
      <td style="text-align:left; color:#f8fafc; font-weight: 600;">${c.label}</td>
      <td>
        <div class="stat-bar-wrapper right">
          <span class="stat-val">${c.homevalue.toFixed(2)}</span>
          <div class="stat-track"><div class="stat-fill home-fill" style="width: ${homePct}%;"></div></div>
        </div>
      </td>
      <td>
        <div class="stat-bar-wrapper left">
          <div class="stat-track"><div class="stat-fill away-fill" style="width: ${awayPct}%;"></div></div>
          <span class="stat-val">${c.awayvalue.toFixed(2)}</span>
        </div>
      </td>
      <td style="font-size: 1.1rem;">${icon}</td>
    </tr>`;
      })
      .join("");

    document.getElementById("stats-table").innerHTML = `
    <table class="stats-compare-table">
      <thead>
        <tr>
          <th>Métrica</th>
          <th>${data.homename}</th>
          <th>${data.awayname}</th>
          <th>Edge</th>
        </tr>
      </thead>
      <tbody>${statsTableBody}</tbody>
    </table>
  `;
  } catch (e) {
    console.error("Error en matriz:", e);
  }

  // ==========================================
  // 2. RADAR CHART (Estilo Neon/Glass)
  // ==========================================
  try {
    const radarCanvas = document.getElementById("radar-chart");
    if (radarCanvas) {
      if (radarChart) radarChart.destroy();
      const rCtx = radarCanvas.getContext("2d");
      const maxVals = data.comparisons.map(
        (c) => Math.max(c.home_value, c.away_value) || 1,
      );

      radarChart = new Chart(rCtx, {
        type: "radar",
        data: {
          labels: data.comparisons.map((c) => c.label),
          datasets: [
            {
              label: data.home_name,
              data: data.comparisons.map(
                (c, i) => (c.home_value / maxVals[i]) * 100,
              ),
              borderColor: "#3b82f6",
              backgroundColor: "rgba(59, 130, 246, 0.25)",
              pointBackgroundColor: "#fff",
              pointBorderColor: "#3b82f6",
              borderWidth: 2,
              fill: true,
              tension: 0.3,
            },
            {
              label: data.away_name,
              data: data.comparisons.map(
                (c, i) => (c.away_value / maxVals[i]) * 100,
              ),
              borderColor: "#f97316",
              backgroundColor: "rgba(249, 115, 22, 0.25)",
              pointBackgroundColor: "#fff",
              pointBorderColor: "#f97316",
              borderWidth: 2,
              fill: true,
              tension: 0.3,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false, // Ahora funciona bien gracias al DIV del HTML
          plugins: {
            legend: {
              position: "bottom",
              labels: { color: "#cbd5e1", font: { family: "Inter", size: 12 } },
            },
          },
          scales: {
            r: {
              grid: { color: "rgba(255, 255, 255, 0.05)" },
              angleLines: { color: "rgba(255, 255, 255, 0.05)" },
              pointLabels: {
                color: "#94a3b8",
                font: { family: "Inter", size: 10 },
              },
              ticks: { display: false },
              suggestedMin: 0,
              suggestedMax: 100,
            },
          },
        },
      });
    }
  } catch (e) {
    console.error("Error Radar:", e);
  }

  // ==========================================
  // 3. NUEVO GRÁFICO: DOUGHNUT DE PROBABILIDADES
  // ==========================================
  try {
    const probCanvas = document.getElementById("prob-chart");
    if (probCanvas) {
      if (probChart) probChart.destroy();
      const pCtx = probCanvas.getContext("2d");

      // Fallback seguro por si data.values está vacío
      const safeValues = data.values || [];
      const pHome =
        safeValues.find(
          (v) =>
            v.selection.includes("Local") || v.selection.includes("Jugador 1"),
        )?.model_prob || 0;
      const pAway =
        safeValues.find(
          (v) =>
            v.selection.includes("Visitante") ||
            v.selection.includes("Jugador 2"),
        )?.model_prob || 0;
      const pDraw =
        safeValues.find((v) => v.selection.includes("Empate"))?.model_prob || 0;

      let probLabels, probData, probColors;
      if (pDraw > 0) {
        probLabels = [data.home_name, "Empate", data.away_name];
        probData = [pHome, pDraw, pAway];
        probColors = ["#3b82f6", "#64748b", "#f97316"];
      } else {
        probLabels = [data.home_name, data.away_name];
        probData = [pHome, pAway];
        probColors = ["#3b82f6", "#f97316"];
      }

      probChart = new Chart(pCtx, {
        type: "doughnut",
        data: {
          labels: probLabels,
          datasets: [
            {
              data: probData,
              backgroundColor: probColors,
              borderWidth: 0,
              hoverOffset: 6,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "70%",
          plugins: {
            legend: {
              position: "right",
              labels: { color: "#cbd5e1", usePointStyle: true, padding: 20 },
            },
            tooltip: {
              callbacks: {
                label: function (context) {
                  return ` ${context.label}: ${context.raw.toFixed(1)}%`;
                },
              },
            },
          },
        },
      });
    }
  } catch (e) {
    console.error("Error Prob Chart:", e);
  }

  // ==========================================
  // 3b. MOST PROBABLE SCORE
  // ==========================================
  try {
    const scoreBox = document.getElementById("most-probable-score-box");
    const scoreValue = document.getElementById("most-probable-score-value");
    const scoreResult = document.getElementById("most-probable-score-result");
    if (scoreBox && scoreValue && data.most_probable_score) {
      scoreBox.style.display = "block";
      scoreValue.textContent = data.most_probable_score;
      // Check if actual result exists in snapshot values
      // The result highlight is set when the snapshot is loaded with final scores
      if (
        data._actual_score_home !== undefined &&
        data._actual_score_away !== undefined
      ) {
        const predictedParts = data.most_probable_score.split("-");
        if (predictedParts.length === 2) {
          const predH = parseInt(predictedParts[0].trim(), 10);
          const predA = parseInt(predictedParts[1].trim(), 10);
          const actualH = data._actual_score_home;
          const actualA = data._actual_score_away;
          const isCorrect = predH === actualH && predA === actualA;
          scoreBox.style.background = isCorrect
            ? "rgba(34,197,94,0.15)"
            : "rgba(239,68,68,0.15)";
          scoreBox.style.borderColor = isCorrect
            ? "rgba(34,197,94,0.35)"
            : "rgba(239,68,68,0.35)";
          scoreValue.style.color = isCorrect ? "#22c55e" : "#ef4444";
          if (scoreResult) {
            scoreResult.style.color = isCorrect ? "#22c55e" : "#ef4444";
            scoreResult.textContent = isCorrect
              ? `✅ Acertó: resultado real ${actualH} - ${actualA}`
              : `❌ Real: ${actualH} - ${actualA}`;
          }
        }
      } else {
        // Reset to default accent style
        scoreBox.style.background = "rgba(99,102,241,0.12)";
        scoreBox.style.borderColor = "rgba(99,102,241,0.25)";
        scoreValue.style.color = "var(--accent)";
        if (scoreResult) scoreResult.textContent = "";
      }
    } else if (scoreBox) {
      scoreBox.style.display = "none";
    }
  } catch (e) {
    console.error("Error Most Probable Score:", e);
  }

  // ==========================================
  // 4. BAR CHART HORIZONTAL
  // ==========================================
  try {
    const barCanvas = document.getElementById("bar-chart");
    if (barCanvas) {
      if (barChart) barChart.destroy();
      const bCtx = barCanvas.getContext("2d");

      // Math.log1p(x) es igual a Math.log(1 + x), evita el -Infinity con ceros
      const normalize = (val) => Math.log1p(Math.max(0, val));

      barChart = new Chart(bCtx, {
        type: "bar",
        data: {
          labels: data.comparisons.map((c) => c.label),
          datasets: [
            {
              label: data.home_name,
              data: data.comparisons.map((c) => normalize(c.home_value)),
              // Guardamos el dato real para el tooltip
              realData: data.comparisons.map((c) => c.home_value),
              backgroundColor: "#3b82f6",
              borderRadius: 4,
            },
            {
              label: data.away_name,
              data: data.comparisons.map((c) => normalize(c.away_value)),
              // Guardamos el dato real para el tooltip
              realData: data.comparisons.map((c) => c.away_value),
              backgroundColor: "#f97316",
              borderRadius: 4,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: "y",
          plugins: {
            legend: { position: "bottom", labels: { color: "#cbd5e1" } },
            tooltip: {
              callbacks: {
                // Leer el valor REAL almacenado en vez del valor logarítmico
                label: function (context) {
                  const realValue = context.dataset.realData[context.dataIndex];
                  return ` ${context.dataset.label}: ${realValue.toFixed(2)}`;
                },
              },
            },
          },
          scales: {
            x: {
              grid: { color: "rgba(255, 255, 255, 0.05)" },
              // Ocultamos los números del eje X porque no significarían nada para el usuario
              ticks: { display: false },
            },
            y: {
              grid: { display: false },
              ticks: { color: "#cbd5e1", font: { size: 10 } },
            },
          },
        },
      });
    }
  } catch (e) {
    console.error("Error Bar Chart:", e);
  }

  // LLM analysis
  const llmBox = document.getElementById("llm-analysis");
  const content =
    data.llm_analysis || "Sherlock quiere analizar las estadísticas...";
  const isPlaceholder = !data.llm_analysis;

  llmBox.innerHTML = `
  <div class="llm-box">
    <h3>🤖 Veredicto Sherlock</h3>
    <div class="llm-body ${isPlaceholder ? "llm-body--placeholder" : ""}">
      ${
        isPlaceholder
          ? `<p>${content}</p>`
          : `<p>${renderMarkdown(content)}</p>`
      }
    </div>
  </div>`;
}

// ── Real-Time Value Calculator ──────────────────────────────────
function populateMarketOptions(data) {
  const select = document.getElementById("checker-market");
  if (!select) return;

  select.innerHTML = "";
  if (data.values && data.values.length > 0) {
    data.values.forEach((v, i) => {
      const opt = document.createElement("option");
      opt.value = i;
      opt.textContent = `${v.selection} (Exp: ${v.model_prob.toFixed(1)}%)`;
      select.appendChild(opt);
    });
    // Default values
    const oddsInput = document.getElementById("checker-odds");
    if (oddsInput && data.values[0].odds) {
      oddsInput.value = data.values[0].odds.toFixed(2);
    }
    updateRealTimeValue();
  }
}

function updateRealTimeValue() {
  if (!currentResults) return;
  const select = document.getElementById("checker-market");
  const oddsInput = document.getElementById("checker-odds");
  const resultDiv = document.getElementById("checker-result");

  if (!select || !oddsInput || !resultDiv) return;

  const v = currentResults.values[select.value];
  const bookieOdds = parseFloat(oddsInput.value);

  if (!bookieOdds || bookieOdds <= 1) {
    resultDiv.innerHTML = "";
    return;
  }

  const modelProb = v.model_prob / 100;
  const pushProb = (v.push_prob || 0) / 100;

  // Cálculo de Edge considerando el PUSH (Expected Value)
  // EV = (P_win * Odds) + (P_push * 1) - 1
  const edge = (modelProb * bookieOdds + pushProb - 1) * 100;

  // Simplified Kelly (1/4 Kelly suggested)
  const kellyMultiplier = 0.25;
  const kelly =
    edge > 0 ? (edge / 100 / (bookieOdds - 1)) * kellyMultiplier : 0;

  const color =
    edge > 6.0
      ? "var(--color-success)"
      : edge > 2.5
        ? "#86efac"
        : "var(--color-error)";
  const recommendation =
    edge > 10.0
      ? "🔥 VALOR EXTREMO"
      : edge > 5.0
        ? "✅ VALUE PROFESIONAL"
        : edge > 0
          ? "⚖️ Valor marginal"
          : "❌ SIN VALOR";

  resultDiv.innerHTML = `
    <div style="font-weight:700; color:${color}; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
      <span style="height: 8px; width: 8px; border-radius: 50%; background: ${color}; box-shadow: 0 0 8px ${color}"></span>
      ${recommendation}
    </div>
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:0.75rem; font-size:0.9rem; background: rgba(0,0,0,0.2); padding: 0.75rem; border-radius: 8px;">
      <div style="display: flex; flex-direction: column;">
        <span style="color: var(--text-secondary); font-size: 0.75rem;">Edge</span>
        <span style="font-weight: 700; color: ${color}; font-size: 1.1rem;">${edge.toFixed(1)}%</span>
      </div>
      <div style="display: flex; flex-direction: column;">
        <span style="color: var(--text-secondary); font-size: 0.75rem;">Stake (1/4 Kelly)</span>
        <span style="font-weight: 700; color: var(--text-secondary); font-size: 1.1rem;">${(kelly * 100).toFixed(1)}%</span>
      </div>
    </div>
  `;
}
// ── Persistencia y Resultados ──────────────────────────────────
async function saveAnalysisDataToDB(sport, payload, results = null) {
  try {
    const entry = {
      id: loadedHistoryEntryId,
      sport: sport,
      match_title:
        (payload.home?.name || payload.player1?.name || "Local") +
        " vs " +
        (payload.away?.name || payload.player2?.name || "Visitante"),
      match_date:
        loadedHistoryEntryDate ||
        payload.match_date ||
        new Date().toISOString(),
      payload: payload,
      picks_calculados: results ? results.values : [],
      user_context: payload.context || "",
      llm_response: results && results.llm_analysis ? results.llm_analysis : "",
      llm_timestamp:
        results && results.llm_analysis ? new Date().toISOString() : null,
      compare_response_snapshot: results ? results : null,
      count_in_profitability: document.getElementById("fb-count-profit")
        ? document.getElementById("fb-count-profit").checked
        : true,
    };

    const res = await fetch("/api/v1/analysis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(entry),
    });
    const data = await res.json();
    console.log("Analysis persisted:", data.id);
    // Actualizar el ID cargado con el retornado y limpiar edición
    loadedHistoryEntryId = data.id;
    cancelEditing();
    return data;
  } catch (e) {
    console.error("Error saving to DB:", e);
  }
}

function toggleHistoryModal() {
  const modal = document.getElementById("history-modal");

  // Seguridad extra por si el modal entero no existe
  if (!modal) {
    console.error("El modal 'history-modal' no se encontró en el HTML.");
    return;
  }

  const isVisible = modal.style.display === "flex";

  if (!isVisible) {
    modal.style.display = "flex";
    const sport = document.querySelector(".tab--active").dataset.sport;

    // Verificamos que el select existe antes de asignarle un valor
    const sportSelect = document.getElementById("history-sport-filter");
    if (sportSelect) {
      sportSelect.value = sport;
    }

    loadHistory();
  } else {
    modal.style.display = "none";
  }
}

// ── Cargar y pintar la lista del historial ─────────────────────
async function loadHistory() {
  const sportSelect = document.getElementById("history-sport-filter");
  const sport = sportSelect ? sportSelect.value : "";
  const dateFrom = document.getElementById("history-date-from")?.value || "";
  const dateTo = document.getElementById("history-date-to")?.value || "";

  const list = document.getElementById("history-list");
  if (!list) return;
  list.innerHTML = "<tr><td colspan='5'>Cargando historial...</td></tr>";

  try {
    let url = `/api/v1/analysis?`;
    if (sport) url += `sport=${sport}&`;
    if (dateFrom) url += `match_date_from=${dateFrom}&`;
    if (dateTo) url += `match_date_to=${dateTo}&`;

    const r = await fetch(url);
    const entries = await r.json();

    if (entries.length === 0) {
      list.innerHTML =
        "<tr><td colspan='5'>No hay registros previos que coincidan.</td></tr>";
      return;
    }

    // Guardamos globalmente para filtrar en UI sin recargar
    window._historyEntries = entries;
    renderHistoryList(entries);
  } catch (e) {
    list.innerHTML =
      "<tr><td colspan='5'>Error al cargar el historial.</td></tr>";
  }
}

function renderHistoryList(entries) {
  const list = document.getElementById("history-list");
  if (!list) return;
  list.innerHTML = entries
    .map((e) => {
      let accuracy = "—";
      if (e.accuracy_percentage != null) {
        accuracy = `${e.accuracy_percentage.toFixed(0)}%`;
        if (e.picks_hits_summary) {
          accuracy += ` <small style="opacity: 0.8; font-size: 0.8em;">(${e.picks_hits_summary})</small>`;
        }
      } else if (e.picks_hits_summary) {
        accuracy = `<small style="opacity: 0.8;">(${e.picks_hits_summary})</small>`;
      }

      const accClass =
        e.accuracy_percentage >= 70
          ? "success"
          : e.accuracy_percentage >= 40
            ? "warning"
            : "error";

      let statusDot = "";
      if (e.accuracy_percentage != null) {
        if (e.accuracy_percentage >= 70) statusDot = "🟢";
        else if (e.accuracy_percentage >= 30) statusDot = "🟡";
        else statusDot = "🔴";
      }

      // ── Calcular unidades ganadas/perdidas en este partido ──
      let matchUnits = null;
      let matchUnitsText = "";
      if (e.picks_calculados) {
        try {
          const parsed = typeof e.picks_calculados === "string" ? JSON.parse(e.picks_calculados) : e.picks_calculados;
          const picks = Array.isArray(parsed) ? parsed : [];
          // Si el partido está resuelto, sumamos el beneficio de cada pick
          if (e.accuracy_percentage != null && picks.length > 0) {
            let totalProfit = 0;
            let countProfit = false;
            picks.forEach(p => {
              if (p.success !== null) {
                countProfit = true;
                if (p.success === true) {
                  totalProfit += (p.odds - 1);
                } else if (p.success === false) {
                  totalProfit -= 1;
                }
              }
            });
            if (countProfit) {
              matchUnits = totalProfit;
              const sign = totalProfit >= 0 ? "+" : "";
              const color = totalProfit >= 0 ? "#22c55e" : "#ef4444";
              matchUnitsText = `<span style="color: ${color}; font-weight: bold; margin-left: 6px; font-size: 0.9em;">(${sign}${totalProfit.toFixed(2)}u)</span>`;
            }
          }
        } catch (err) {
          console.warn("Error calculating match profit:", err);
        }
      }

      // ── Determinar categorías de picks ──
      let pickCategories = [];

      // Parsear picks_calculados (string JSON de la BD)
      let picks = [];
      if (e.picks_calculados) {
        try {
          const parsed =
            typeof e.picks_calculados === "string"
              ? JSON.parse(e.picks_calculados)
              : e.picks_calculados;
          picks = Array.isArray(parsed) ? parsed : [];
        } catch {
          picks = [];
        }
      }

      if (picks.length > 0) {
        const hasProfessional = picks.some(
          (p) =>
            p.is_publishable === true ||
            (p.is_value === true &&
              p.is_underdog !== true &&
              p.is_high_confidence !== true),
        );
        const hasUnderdog = picks.some((p) => p.is_underdog === true);
        const hasHighConfidence = picks.some(
          (p) => p.is_high_confidence === true,
        );

        if (hasProfessional)
          pickCategories.push({
            label: "Profesional",
            icon: "🎯",
            color: "#4CAF50",
          });
        if (hasUnderdog)
          pickCategories.push({
            label: "Underdog",
            icon: "🚀",
            color: "#FF9800",
          });
        if (hasHighConfidence)
          pickCategories.push({
            label: "Alta Confianza",
            icon: "⭐",
            color: "#FFD700",
          });
      }

      // Construir los badges de categorías
      let categoryBadges = "";
      if (pickCategories.length === 0) {
        categoryBadges = `<span title="Sin Picks" style="margin-right: 5px; opacity: 0.3; cursor: help;">⭕</span>`;
      } else {
        categoryBadges = pickCategories
          .map(
            (cat) =>
              `<span title="${cat.label}" style="margin-right: 4px; cursor: help; font-size: 0.9em;">${cat.icon}</span>`,
          )
          .join("");
      }

      let competition = "—";
      if (e.payload) {
        try {
          const p =
            typeof e.payload === "string" ? JSON.parse(e.payload) : e.payload;
          if (p.competition) competition = p.competition;
        } catch {}
      }

      return `
      <tr>
        <td>${new Date(e.match_date || e.date).toLocaleDateString()}</td>
        <td style="font-size: 0.85em; color: var(--color-text-muted, #94a3b8);">${competition}</td>
        <td style="text-align: left;">
          ${categoryBadges}
          ${e.match_title} ${statusDot} ${matchUnitsText}
        </td>
        <td><span class="badge badge--${accClass}">${accuracy}</span></td>
        <td>
          <div style="display: flex; gap: 0.4rem; justify-content: center;">
            <button class="btn-preset" title="Cargar Datos" onclick="loadHistoryEntry('${e.id}')">📂</button>
            <button class="btn-preset" title="Reanalizar" onclick="reanalyzeHistoryEntry('${e.id}')">🔄</button>
            <button class="btn-preset" title="Registrar Resultado" onclick="openResultsModal('${e.id}', '${e.match_title}')">🏆</button>
            <button class="btn-preset" style="color: var(--red);" title="Eliminar" onclick="deleteHistoryEntry('${e.id}')">🗑️</button>
          </div>
        </td>
      </tr>
    `;
    })
    .join("");
}

function filterHistoryUI() {
  const query = document.getElementById("history-search").value.toLowerCase();
  if (!window._historyEntries) return;

  const filtered = window._historyEntries.filter(
    (e) =>
      e.match_title.toLowerCase().includes(query) ||
      e.sport.toLowerCase().includes(query),
  );
  renderHistoryList(filtered);
}

async function recalculateAllHistoryAccuracy() {
  if (
    !confirm(
      "¿Deseas recalcular la precisión de todos los partidos que tienen resultados registrados? Esto aplicará los nuevos criterios de filtrado a todo el historial.",
    )
  )
    return;

  try {
    const btn = event.target;
    const originalText = btn.innerHTML;
    btn.innerHTML = "⏳ Recalculando...";
    btn.disabled = true;

    const response = await fetch("/api/v1/analysis/recalculate-all", {
      method: "POST",
    });

    if (!response.ok) {
      throw new Error("Error en el servidor al recalcular.");
    }

    const data = await response.json();
    alert(`✅ ¡Hecho! ${data.message}`);

    // Refrescar historial
    loadHistory();

    // Si el modal de estadísticas está abierto, también sería bueno actualizarlo
    if (typeof loadGlobalStats === "function") {
      loadGlobalStats();
    }

    btn.innerHTML = originalText;
    btn.disabled = false;
  } catch (error) {
    console.error("Error al recalcular todo:", error);
    alert("Hubo un error al procesar la solicitud.");
  }
}

// ── Eliminar un análisis del historial ─────────────────────────
async function deleteHistoryEntry(id) {
  if (!confirm("¿Estás seguro de que deseas eliminar este registro?")) return;

  try {
    const response = await fetch(`/api/v1/analysis/${id}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error("No se pudo eliminar el registro de la BD.");
    }

    // ✅ Busca el elemento de forma segura antes de leer .value
    const sportSelect = document.getElementById("history-sport-filter");
    const currentSport = sportSelect ? sportSelect.value : "";

    loadHistory();
  } catch (error) {
    console.error("Error al eliminar:", error);
    alert(error.message);
  }
}

// Función auxiliar para evitar errores si el input no existe en el HTML
function setSafeValue(id, value) {
  const el = document.getElementById(id);
  if (el) {
    el.value = value !== null && value !== undefined ? value : "";
  }
}

async function loadHistoryEntry(id) {
  try {
    const r = await fetch(`/api/v1/analysis/${id}`);
    const entry = await r.json();

    if (entry && entry.payload) {
      // Tu backend guarda payload como string JSON
      const payload =
        typeof entry.payload === "string"
          ? JSON.parse(entry.payload)
          : entry.payload;

      // Guardar ID y fecha de edición
      loadedHistoryEntryId = entry.id;
      loadedHistoryEntryDate = entry.match_date || entry.date;

      if (document.getElementById("fb-count-profit")) {
        document.getElementById("fb-count-profit").checked =
          entry.count_in_profitability !== false;
      }

      // Mostrar indicador de edición
      const indicator = document.getElementById("editing-indicator");
      const matchName = document.getElementById("editing-match-name");
      if (indicator && matchName) {
        matchName.textContent =
          entry.match_title || `${payload.home?.name} vs ${payload.away?.name}`;
        indicator.style.display = "flex";
      }

      populateAppForm(entry.sport, payload);
      toggleHistoryModal();

      if (entry.compare_response_snapshot && !entry.needs_reanalysis) {
        const snapshot =
          typeof entry.compare_response_snapshot === "string"
            ? JSON.parse(entry.compare_response_snapshot)
            : entry.compare_response_snapshot;

        currentSport = entry.sport;
        currentPayload = payload;
        window._currentSnapshot = snapshot;

        // Inject actual scores into snapshot for most_probable_score highlighting
        if (
          entry.final_score_home !== null &&
          entry.final_score_home !== undefined
        ) {
          snapshot._actual_score_home = entry.final_score_home;
          snapshot._actual_score_away = entry.final_score_away;
        }

        if (entry.sport === "football") {
          renderResults(snapshot);
        }

        if (entry.llm_response) {
          const llmBox = document.getElementById("llm-analysis");
          const btn = document.getElementById("btn-sherlock-analysis");
          const streamingEl = document.getElementById("llm-streaming-text");
          if (llmBox && !streamingEl) {
            llmBox.innerHTML = `
                  <div class="llm-box">
                      <h3>🔍 Veredicto Sherlock</h3>
                      <div class="llm-body" id="llm-streaming-text" style="color: var(--color-text-muted, #94a3b8)">
                          ${renderMarkdown(entry.llm_response)}
                      </div>
                  </div>`;
          } else if (streamingEl) {
            streamingEl.innerHTML = renderMarkdown(entry.llm_response);
          }
          if (btn) {
            btn.innerHTML = "✅ Veredicto generado — pedir de nuevo";
          }
        }
      }
    }
  } catch (e) {
    console.error("Error loading history entry:", e);
    showError("Error al cargar la entrada del historial.");
  }
}

async function reanalyzeHistoryEntry(id) {
  if (
    !confirm(
      "¿Deseas descartar el snapshot actual y recalcular el análisis para este partido?",
    )
  )
    return;
  try {
    const r = await fetch(`/api/v1/analysis/${id}`);
    const entry = await r.json();
    if (entry && entry.payload) {
      // Set needs_reanalysis to true in DB
      await fetch(`/api/v1/analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sport: entry.sport,
          match_title: entry.match_title,
          payload:
            typeof entry.payload === "string"
              ? JSON.parse(entry.payload)
              : entry.payload,
          needs_reanalysis: true,
        }),
      });

      const payload =
        typeof entry.payload === "string"
          ? JSON.parse(entry.payload)
          : entry.payload;
      populateAppForm(entry.sport, payload);
      toggleHistoryModal();

      // Trigger specific sport analysis
      if (entry.sport === "football") analyzeFootball();
    }
  } catch (e) {
    showError("Error al reanalizar.");
  }
}

function cancelEditing() {
  loadedHistoryEntryId = null;
  loadedHistoryEntryDate = null;
  const indicator = document.getElementById("editing-indicator");
  if (indicator) {
    indicator.style.display = "none";
  }
  if (document.getElementById("fb-count-profit")) {
    document.getElementById("fb-count-profit").checked = true;
  }
}

function populateAppForm(sport, data) {
  // Activate tab
  const tab = document.querySelector(`.tab[data-sport="${sport}"]`);
  if (tab) tab.click();

  if (sport === "football") {
    const { home, away, odds } = data;

    // Update prefill banner state to "Loaded"
    const banner = document.getElementById("prefill-banner");
    if (banner) {
      banner.style.background =
        "linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(5, 150, 105, 0.2))";
      banner.style.border = "1px solid rgba(16, 185, 129, 0.3)";
    }
    const bannerIcon = document.getElementById("prefill-icon");
    if (bannerIcon) {
      bannerIcon.textContent = "⚡";
      bannerIcon.style.color = "#10b981";
      bannerIcon.style.opacity = "1";
    }
    const bannerTitle = document.getElementById("prefill-title");
    if (bannerTitle) {
      bannerTitle.style.color = "#10b981";
      bannerTitle.innerHTML = `
        Datos Cargados Automáticamente
        <span id="prefill-badge" style="background: #10b981; color: #fff; font-size: 0.6rem; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; letter-spacing: 1px;">Prefill Activo</span>
      `;
    }
    const bannerDesc = document.getElementById("prefill-desc");
    if (bannerDesc) {
      bannerDesc.textContent =
        "El comparador ha inyectado el historial del partido. Puedes revisar directamente los paneles abajo.";
    }

    if (home) {
      setSafeValue("fb-home-name", home.name);
      const prefillHome = document.getElementById("prefill-home-team");
      if (prefillHome) {
        prefillHome.textContent = home.name || "Local";
        prefillHome.style.color = "var(--text-primary)";
      }
      setSafeValue("fb-home-matches-home", home.matches_home);
      setSafeValue("fb-home-matches-away", home.matches_away);
      setSafeValue("fb-home-wins", home.wins);
      setSafeValue("fb-home-draws", home.draws);
      setSafeValue("fb-home-losses", home.losses);
      setSafeValue("fb-home-goals-per-game", home.goals_per_game);
      setSafeValue("fb-home-goals-conceded", home.goals_conceded_per_game);
      setSafeValue("fb-home-goal-conv", home.goal_conversion_pct);
      setSafeValue("fb-home-big-chances", home.big_chances_per_game);
      setSafeValue(
        "fb-home-big-chances-missed",
        home.big_chances_missed_per_game,
      );
      setSafeValue("fb-home-shots", home.shots_per_game);
      setSafeValue("fb-home-shots-target", home.shots_on_target_per_game);
      setSafeValue("fb-home-possession", home.possession_pct);
      setSafeValue("fb-home-pass", home.passes_completed);
      setSafeValue("fb-home-pass-acc", home.pass_accuracy);
      setSafeValue("fb-home-pass-opp-half", home.passes_opp_half);
      setSafeValue("fb-home-pass-opp", home.pass_accuracy_opp_half);
      setSafeValue("fb-home-cross-completed", home.crosses_per_game);
      setSafeValue("fb-home-cross-acc", home.cross_accuracy);
      setSafeValue("fb-home-corners", home.corners_per_game);
      setSafeValue("fb-home-clean-sheets-home", home.clean_sheets_home);
      setSafeValue("fb-home-clean-sheets-away", home.clean_sheets_away);
      setSafeValue("fb-home-saves", home.saves_per_game);
      setSafeValue("fb-home-balls-recovered", home.balls_recovered_per_game);
      setSafeValue("fb-home-duels", home.duels_won_per_game);
      setSafeValue("fb-home-duels-ground", home.ground_duels_won_per_game);
      setSafeValue("fb-home-pen-conceded", home.penalties_conceded);
      setSafeValue("fb-home-fouls", home.fouls_per_game);
      setSafeValue("fb-home-yellow-cards", home.yellow_cards_per_game);
      setSafeValue("fb-home-red-cards", home.red_cards_total);
      setSafeValue("fb-home-offsides", home.offside_per_game);
      setSafeValue("fb-home-errors-goal", home.errors_leading_to_goal);
      setSafeValue("fb-home-xg", home.xg_per_game);
      setSafeValue("fb-home-xga", home.xga_per_game);
      setSafeValue("fb-home-corners-conceded", home.corners_conceded_per_game);
    }

    if (away) {
      setSafeValue("fb-away-name", away.name);
      const prefillAway = document.getElementById("prefill-away-team");
      if (prefillAway) {
        prefillAway.textContent = away.name || "Visitante";
        prefillAway.style.color = "var(--text-primary)";
      }
      setSafeValue("fb-away-matches-home", away.matches_home);
      setSafeValue("fb-away-matches-away", away.matches_away);
      setSafeValue("fb-away-wins", away.wins);
      setSafeValue("fb-away-draws", away.draws);
      setSafeValue("fb-away-losses", away.losses);
      setSafeValue("fb-away-goals-per-game", away.goals_per_game);
      setSafeValue("fb-away-goals-conceded", away.goals_conceded_per_game);
      setSafeValue("fb-away-goal-conv", away.goal_conversion_pct);
      setSafeValue("fb-away-big-chances", away.big_chances_per_game);
      setSafeValue(
        "fb-away-big-chances-missed",
        away.big_chances_missed_per_game,
      );
      setSafeValue("fb-away-shots", away.shots_per_game);
      setSafeValue("fb-away-shots-target", away.shots_on_target_per_game);
      setSafeValue("fb-away-possession", away.possession_pct);
      setSafeValue("fb-away-pass", away.passes_completed);
      setSafeValue("fb-away-pass-acc", away.pass_accuracy);
      setSafeValue("fb-away-pass-opp-half", away.passes_opp_half);
      setSafeValue("fb-away-pass-opp", away.pass_accuracy_opp_half);
      setSafeValue("fb-away-cross-completed", away.crosses_per_game);
      setSafeValue("fb-away-cross-acc", away.cross_accuracy);
      setSafeValue("fb-away-corners", away.corners_per_game);
      setSafeValue("fb-away-clean-sheets-home", away.clean_sheets_home);
      setSafeValue("fb-away-clean-sheets-away", away.clean_sheets_away);
      setSafeValue("fb-away-saves", away.saves_per_game);
      setSafeValue("fb-away-balls-recovered", away.balls_recovered_per_game);
      setSafeValue("fb-away-duels", away.duels_won_per_game);
      setSafeValue("fb-away-duels-ground", away.ground_duels_won_per_game);
      setSafeValue("fb-away-pen-conceded", away.penalties_conceded);
      setSafeValue("fb-away-fouls", away.fouls_per_game);
      setSafeValue("fb-away-yellow-cards", away.yellow_cards_per_game);
      setSafeValue("fb-away-red-cards", away.red_cards_total);
      setSafeValue("fb-away-offsides", away.offside_per_game);
      setSafeValue("fb-away-errors-goal", away.errors_leading_to_goal);
      setSafeValue("fb-away-xg", away.xg_per_game);
      setSafeValue("fb-away-xga", away.xga_per_game);
      setSafeValue("fb-away-corners-conceded", away.corners_conceded_per_game);
    }

    if (data.competition) {
      setSafeValue("fb-competition", data.competition);
    }
    if (data.league_stats) {
      setSafeValue("fb-league-goals", data.league_stats.avg_goals_per_game);
      setSafeValue("fb-league-corners", data.league_stats.avg_corners_per_game);
      setSafeValue("fb-league-cards", data.league_stats.avg_cards_per_game);
      setSafeValue("fb-league-yellow-cards", data.league_stats.avg_yellow_cards_per_game);
      setSafeValue("fb-league-red-cards", data.league_stats.avg_red_cards_per_game);
      setSafeValue("fb-referee-yellow", data.league_stats.referee_avg_yellow);
      setSafeValue("fb-referee-red", data.league_stats.referee_avg_red);
    }

    if (odds) {
      setSafeValue("fb-bookmaker", odds.bookmaker);
      setSafeValue("fb-odds-home", odds.home);
      setSafeValue("fb-odds-draw", odds.draw);
      setSafeValue("fb-odds-away", odds.away);
      setSafeValue("fb-odds-over25", odds.over_25);
      setSafeValue("fb-odds-under25", odds.under_25);
      setSafeValue("fb-odds-btts-yes", odds.btts_yes);
      setSafeValue("fb-odds-btts-no", odds.btts_no);
      setSafeValue("fb-odds-dc-1x", odds.dc_1x);
      setSafeValue("fb-odds-dc-x2", odds.dc_x2);
      setSafeValue("fb-odds-dc-12", odds.dc_12);
      setSafeValue("fb-odds-dnb-home", odds.dnb_home);
      setSafeValue("fb-odds-dnb-away", odds.dnb_away);

      const populateTable = (tbodyId, lines, overOdds, underOdds) => {
        const tb = document.getElementById(tbodyId);
        if (!tb) return;
        tb.innerHTML = ""; // Clear existing rows
        if (lines && lines.length > 0) {
          lines.forEach((line) => {
            const over =
              overOdds && overOdds[line] !== undefined ? overOdds[line] : "";
            const under =
              underOdds && underOdds[line] !== undefined ? underOdds[line] : "";
            const tr = document.createElement("tr");
            tr.innerHTML = `
              <td><input type="number" step="0.01" class="input" style="padding: 0.2rem; text-align: center" value="${line}" /></td>
              <td><input type="number" step="0.01" class="input" style="padding: 0.2rem; text-align: center" value="${over}" /></td>
              <td><input type="number" step="0.01" class="input" style="padding: 0.2rem; text-align: center" value="${under}" /></td>
            `;
            tb.appendChild(tr);
          });
        }
      };

      populateTable(
        "goals-odds-tbody",
        odds.goals_lines || ["1.5", "2.5", "3.5", "4.5"],
        odds.goalsOverOdds,
        odds.goalsUnderOdds,
      );
      populateTable(
        "corners-odds-tbody",
        odds.corners_lines || ["7.5", "8.5", "9.5", "10.5"],
        odds.cornersOverOdds,
        odds.cornersUnderOdds,
      );
      populateTable(
        "cards-odds-tbody",
        odds.cards_lines || ["2.5", "3.5", "4.5", "5.5"],
        odds.cardsOverOdds,
        odds.cardsUnderOdds,
      );
      populateTable(
        "shots-odds-tbody",
        odds.shots_lines || ["21.5", "22.5", "23.5", "24.5"],
        odds.shotsOverOdds,
        odds.shotsUnderOdds,
      );
      populateTable(
        "shots-target-odds-tbody",
        odds.shots_target_lines || ["7.5", "8.5", "9.5", "10.5"],
        odds.shotsTargetOverOdds,
        odds.shotsTargetUnderOdds,
      );
    }
  }
}

// ── API call ─────────────────────────────────────────────────────
async function apiCompare(sport, payload) {
  const searchingEl = document.getElementById("searching-step");
  const resultsEl = document.getElementById("results");
  if (searchingEl) searchingEl.style.display = "block";
  if (resultsEl) resultsEl.style.display = "none";
  try {
    // Forzar llm desactivado en la primera llamada
    const cleanPayload = { ...payload, generatellmanalysis: false };
    const r = await fetch(`/api/v1/compare/${sport}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cleanPayload),
    });
    if (!r.ok) {
      const e = await r.json();
      showError(e.detail || "Error en el servidor");
      return null;
    }
    const data = await r.json();
    if (searchingEl) searchingEl.style.display = "none";
    return data;
  } catch (e) {
    showError("Error de conexión: " + e.message);
    if (searchingEl) searchingEl.style.display = "none";
    return null;
  }
}

async function streamLlmAnalysis(sport, payload) {
  const llmBox = document.getElementById("llm-analysis");
  if (!llmBox) return;

  // Mostrar placeholder con spinner mientras espera
  llmBox.innerHTML = `
      <div class="llm-box">
          <h3>🔍 Veredicto Sherlock</h3>
          <div class="llm-body llm-body--placeholder" id="llm-streaming-text">
              <span class="llm-spinner">⏳</span> Sherlock quiere analizar las estadísticas...
          </div>
      </div>`;

  const endpointMap = { football: "football" };
  const url = `/api/v1/compare/${endpointMap[sport]}/analysis`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const streamingEl = document.getElementById("llm-streaming-text");
    if (streamingEl) streamingEl.innerHTML = ""; // limpiar placeholder

    let buffer = "";
    let fullText = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Parsear eventos SSE del buffer
      const lines = buffer.split("\n");
      buffer = lines.pop(); // guardar línea incompleta

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (raw === "[DONE]") break;
        try {
          const parsed = JSON.parse(raw);
          if (parsed.error) {
            if (streamingEl)
              streamingEl.innerHTML = `<p style="color:var(--color-notification)">${parsed.error}</p>`;
            return;
          }
          if (parsed.chunk) {
            fullText += parsed.chunk;
            // Renderizar markdown incremental
            if (streamingEl) streamingEl.innerHTML = renderMarkdown(fullText);
          }
        } catch (_) {}
      }
    }

    if (fullText.trim() && window._currentSnapshot) {
      const snap = { ...window._currentSnapshot, llm_analysis: fullText };
      window._currentSnapshot = snap;
      await saveAnalysisDataToDB(sport, payload, snap);
    }
  } catch (e) {
    const streamingEl = document.getElementById("llm-streaming-text");
    if (streamingEl)
      streamingEl.innerHTML = `<p>Error al cargar el análisis: ${e.message}</p>`;
  }
}

function validatePayload(payload, sport) {
  let missing = [];
  const check = (obj, prefix) => {
    for (let k in obj) {
      if (
        obj[k] === 0 ||
        obj[k] === "" ||
        obj[k] === null ||
        obj[k] === undefined
      ) {
        // Ignorar ids o campos no críticos si quieres, pero por ahora reportamos 0s
        if (k !== "name" && obj[k] === 0) {
          missing.push(`${prefix}: ${k}`);
        }
      }
    }
  };

  // Solo aviso, no bloqueo
  if (missing.length > 5) {
    return confirm(
      `⚠️ Sherlock nota que faltan datos (${missing.length} campos en 0). ¿Deseas continuar con la deducción de todos modos?`,
    );
  }
  return true;
}

// ═══ FOOTBALL ═══
// ═══ FOOTBALL ═══
function _fbTeam(p) {
  return {
    name: val(`fb-${p}-name`),
    matches_home: val(`fb-${p}-matches-home`),
    matches_away: val(`fb-${p}-matches-away`),
    matches_played:
      (val(`fb-${p}-matches-home`) || 0) + (val(`fb-${p}-matches-away`) || 0),
    wins: val(`fb-${p}-wins`),
    draws: val(`fb-${p}-draws`),
    losses: val(`fb-${p}-losses`),
    goals_per_game: val(`fb-${p}-goals-per-game`),
    goals_conceded_per_game: val(`fb-${p}-goals-conceded`),
    goal_conversion_pct: val(`fb-${p}-goal-conv`),
    big_chances_per_game: val(`fb-${p}-big-chances`),
    big_chances_missed_per_game: val(`fb-${p}-big-chances-missed`),
    shots_per_game: val(`fb-${p}-shots`),
    shots_on_target_per_game: val(`fb-${p}-shots-target`),
    possession_pct: val(`fb-${p}-possession`),
    passes_completed: val(`fb-${p}-pass`),
    pass_accuracy: val(`fb-${p}-pass-acc`),
    passes_opp_half: val(`fb-${p}-pass-opp-half`),
    pass_accuracy_opp_half: val(`fb-${p}-pass-opp`),
    crosses_per_game: val(`fb-${p}-cross-completed`),
    cross_accuracy: val(`fb-${p}-cross-acc`),
    corners_per_game: val(`fb-${p}-corners`),
    clean_sheets_home: val(`fb-${p}-clean-sheets-home`),
    clean_sheets_away: val(`fb-${p}-clean-sheets-away`),
    clean_sheets:
      (val(`fb-${p}-clean-sheets-home`) || 0) +
      (val(`fb-${p}-clean-sheets-away`) || 0),
    saves_per_game: val(`fb-${p}-saves`),
    balls_recovered_per_game: val(`fb-${p}-balls-recovered`),
    duels_won_per_game: val(`fb-${p}-duels`),
    ground_duels_won_per_game: val(`fb-${p}-duels-ground`),
    penalties_conceded: val(`fb-${p}-pen-conceded`),
    fouls_per_game: val(`fb-${p}-fouls`),
    yellow_cards_per_game: val(`fb-${p}-yellow-cards`),
    red_cards_total: val(`fb-${p}-red-cards`),
    offside_per_game: val(`fb-${p}-offsides`),
    errors_leading_to_goal: val(`fb-${p}-errors-goal`),
    // Nuevos campos granularidad avanzada
    xg_per_game: val(`fb-${p}-xg`),
    xga_per_game: val(`fb-${p}-xga`),
    corners_conceded_per_game: val(`fb-${p}-corners-conceded`),
    // Cálculos on-the-fly para enviar al backend
    passes_total_per_game:
      (val(`fb-${p}-pass`) * 100) / (val(`fb-${p}-pass-acc`) || 1),
    passes_opp_half_total_per_game:
      (val(`fb-${p}-pass-opp-half`) * 100) / (val(`fb-${p}-pass-opp`) || 1),
    crosses_total_per_game:
      (val(`fb-${p}-cross-completed`) * 100) / (val(`fb-${p}-cross-acc`) || 1),
  };
}

function addOddsLine(type) {
  let tbId = "";
  if (type === "goals") tbId = "goals-odds-tbody";
  else if (type === "corners") tbId = "corners-odds-tbody";
  else if (type === "cards") tbId = "cards-odds-tbody";
  else if (type === "shots") tbId = "shots-odds-tbody";
  else if (type === "shots-target") tbId = "shots-target-odds-tbody";

  const tb = document.getElementById(tbId);
  if (!tb) return;

  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><input type="number" step="0.01" class="input" style="padding: 0.2rem; text-align: center" placeholder="Ej: 5.5" /></td>
    <td><input type="number" step="0.01" class="input" style="padding: 0.2rem; text-align: center" placeholder="" /></td>
    <td><input type="number" step="0.01" class="input" style="padding: 0.2rem; text-align: center" placeholder="" /></td>
  `;
  tb.appendChild(tr);
}

function buildFootballPayloadFromForm() {
  const home = _fbTeam("home");
  const away = _fbTeam("away");

  const getSafeNumber = (id, defaultValue) => {
    const el = document.getElementById(id);
    if (!el || el.value === "") return defaultValue;
    const num = parseFloat(el.value);
    return isNaN(num) ? defaultValue : num;
  };

  function getVal(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    const val = parseFloat(el.value);
    return isNaN(val) ? null : val;
  }

  const getOddsFromTable = (tbodyId) => {
    const lines = [];
    const overOdds = {};
    const underOdds = {};
    const tb = document.getElementById(tbodyId);
    if (tb) {
      tb.querySelectorAll("tr").forEach((tr) => {
        let lineVal = null;
        const inputLine = tr.children[0].querySelector("input");
        if (inputLine) {
          if (inputLine.value) lineVal = inputLine.value.trim();
        } else {
          lineVal = tr.children[0].innerText.trim();
        }

        const inputOver = tr.children[1].querySelector("input");
        const inputUnder = tr.children[2].querySelector("input");

        if (lineVal) {
          let added = false;
          if (
            inputOver &&
            inputOver.value &&
            !isNaN(parseFloat(inputOver.value))
          ) {
            overOdds[lineVal] = parseFloat(inputOver.value);
            added = true;
          }
          if (
            inputUnder &&
            inputUnder.value &&
            !isNaN(parseFloat(inputUnder.value))
          ) {
            underOdds[lineVal] = parseFloat(inputUnder.value);
            added = true;
          }
          // Only include line if at least one odd was provided. But if user adds line dynamically, it might be partial. Wait, allow empty as well if lineVal is there. Actually only push if there are odds.
          if (added) lines.push(lineVal);
        }
      });
    }
    return { lines, overOdds, underOdds };
  };

  const goalsParsed = getOddsFromTable("goals-odds-tbody");
  const cornersParsed = getOddsFromTable("corners-odds-tbody");
  const cardsParsed = getOddsFromTable("cards-odds-tbody");
  const shotsParsed = getOddsFromTable("shots-odds-tbody");
  const shotsTargetParsed = getOddsFromTable("shots-target-odds-tbody");

  const odds = {
    home: getVal("fb-odds-home"),
    draw: getVal("fb-odds-draw"),
    away: getVal("fb-odds-away"),
    btts_yes: getVal("fb-odds-btts-yes"),
    btts_no: getVal("fb-odds-btts-no"),
    dc_1x: getVal("fb-odds-dc-1x"),
    dc_x2: getVal("fb-odds-dc-x2"),
    dc_12: getVal("fb-odds-dc-12"),
    dnb_home: getVal("fb-odds-dnb-home"),
    dnb_away: getVal("fb-odds-dnb-away"),

    goals_lines: goalsParsed.lines,
    goalsOverOdds: goalsParsed.overOdds,
    goalsUnderOdds: goalsParsed.underOdds,

    corners_lines: cornersParsed.lines,
    cornersOverOdds: cornersParsed.overOdds,
    cornersUnderOdds: cornersParsed.underOdds,

    cards_lines: cardsParsed.lines,
    cardsOverOdds: cardsParsed.overOdds,
    cardsUnderOdds: cardsParsed.underOdds,

    shots_lines: shotsParsed.lines,
    shotsOverOdds: shotsParsed.overOdds,
    shotsUnderOdds: shotsParsed.underOdds,

    shots_target_lines: shotsTargetParsed.lines,
    shotsTargetOverOdds: shotsTargetParsed.overOdds,
    shotsTargetUnderOdds: shotsTargetParsed.underOdds,
  };

  const competition = val("fb-competition") || "General";

  const league_stats = {
    avg_goals_per_game: getSafeNumber("fb-league-goals", 2.74),
    avg_corners_per_game: getSafeNumber("fb-league-corners", 9.5),
    avg_cards_per_game: getSafeNumber("fb-league-cards", 4.5),
    avg_yellow_cards_per_game: getSafeNumber("fb-league-yellow-cards", 4.0),
    avg_red_cards_per_game: getSafeNumber("fb-league-red-cards", 0.2),
    referee_avg_yellow: getSafeNumber("fb-referee-yellow", 0.0),
    referee_avg_red: getSafeNumber("fb-referee-red", 0.0),
  };

  return { home, away, odds, competition, league_stats };
}

async function analyzeFootball() {
  const payload = buildFootballPayloadFromForm();
  if (!payload.home.name || !payload.away.name)
    return showError("Ingresa los nombres de ambos equipos");
  if (!validatePayload(payload, "football")) return;
  currentSport = "football";
  currentPayload = payload;

  // FASE 1: stats + gráficos → inmediato
  const data = await apiCompare("football", {
    ...payload,
    generatellmanalysis: false,
  });
  if (!data) return;
  window._currentSnapshot = data;
  renderResults(data);

  // Persistir en DB inmediatamente para tener el registro
  await saveAnalysisDataToDB("football", payload, data);

  // FASE 2: análisis LLM (Opcional si ya existe en DB, pero aquí es nuevo análisis)
  // streamLlmAnalysis("football", payload);
}

function saveFootballPreset() {
  const payload = buildFootballPayloadFromForm();
  if (!payload.home.name || !payload.away.name)
    return showError("Completa al menos los nombres de los equipos.");

  const fileContent = JSON.stringify(
    {
      sport: "football",
      version: "0.5",
      timestamp: new Date().toISOString(),
      data: payload,
    },
    null,
    2,
  );

  const blob = new Blob([fileContent], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download =
    `sherlock_football_${payload.home.name}_vs_${payload.away.name}.json`.replace(
      /\s+/g,
      "_",
    );
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function loadFootballPreset(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const json = JSON.parse(e.target.result);
      if (json.sport === "football" && json.data) {
        populateAppForm("football", json.data);
      }
    } catch (err) {
      showError("Error al cargar preset");
    }
  };
  reader.readAsText(file);
}

// ── Guardar en Base de Datos (Analysis History) ──────────────────
async function saveToDB() {
  try {
    // Detectar el deporte activo
    const activeTab = document.querySelector(".tab--active");
    const sport = activeTab ? activeTab.dataset.sport : "football";

    var payload;
    var matchTitle;

    if (sport === "football") {
      payload = buildFootballPayloadFromForm();
      if (!payload.home.name || !payload.away.name) {
        return showError(
          "Debes ingresar los nombres de los equipos antes de guardar.",
        );
      }
      matchTitle = `${payload.home.name} vs ${payload.away.name}`;
    }
    // Verificamos que al menos haya nombres de equipos
    if (!payload.home.name || !payload.away.name) {
      return showError(
        "Debes ingresar los nombres de los equipos antes de guardar.",
      );
    }

    const dbPayload = {
      id: loadedHistoryEntryId,
      sport: sport,
      match_title: matchTitle,
      match_date: loadedHistoryEntryDate || payload.match_date || null,
      payload: payload,
      count_in_profitability: document.getElementById("fb-count-profit")
        ? document.getElementById("fb-count-profit").checked
        : true,
    };

    // Opcional: mostrar un indicador de carga al usuario
    const btn = document.querySelector('button[onclick="saveToDB()"]');
    if (btn) {
      btn.innerHTML = "Guardando...";
      btn.disabled = true;
    }

    // 3. Enviamos la petición al endpoint correcto de FastAPI
    try {
      const response = await fetch("/api/v1/analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dbPayload),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || "Error al guardar en la base de datos",
        );
      }
      const msg = loadedHistoryEntryId
        ? "Registro actualizado exitosamente ✅"
        : "Análisis guardado exitosamente en la BD ✅";
      cancelEditing();
      alert(msg);
    } catch (error) {
      console.error("Error saving to DB", error);
      showError(error.message);
    } finally {
      if (btn) {
        btn.innerHTML = "Guardar en BD";
        btn.disabled = false;
      }
    }
  } catch (error) {
    console.error("Error saving to DB:", error);
    showError(error.message);
  } finally {
    // Restaurar el botón
    const btn = document.querySelector('button[onclick="saveToDB()"]');
    if (btn) {
      btn.innerHTML = "☁️ Guardar en BD";
      btn.disabled = false;
    }
  }
}

async function requestSherlockAnalysis() {
  if (!currentSport || !currentPayload) {
    showError(
      "Primero ejecuta un análisis estadístico antes de pedir el veredicto.",
    );
    return;
  }

  const btn = document.getElementById("btn-sherlock-analysis");
  const llmBox = document.getElementById("llm-analysis");

  // Deshabilitar botón mientras carga
  btn.disabled = true;
  btn.innerHTML = "⏳ Analizando...";
  btn.style.opacity = "0.7";

  // Mostrar placeholder animado
  llmBox.innerHTML = `
      <div class="llm-box">
          <h3>🔍 Veredicto Sherlock</h3>
          <div class="llm-body" id="llm-streaming-text" style="min-height:60px; color: var(--color-text-muted, #94a3b8)">
              <em>Sherlock está leyendo las estadísticas...</em>
          </div>
      </div>`;

  // Obtener contexto adicional del textarea
  const contextEl = document.getElementById("llm-context");
  const userContext = contextEl ? contextEl.value.trim() : "";

  const endpointMap = { football: "football" };
  const url = `/api/v1/compare/${endpointMap[currentSport]}/analysis`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...currentPayload,
        user_context: userContext,
        generatellmanalysis: false,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const streamingEl = document.getElementById("llm-streaming-text");
    if (streamingEl) streamingEl.innerHTML = "";

    let buffer = "";
    let fullText = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop(); // guarda línea incompleta

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (raw === "[DONE]") break;
        try {
          const parsed = JSON.parse(raw);
          if (parsed.error) {
            if (streamingEl)
              streamingEl.innerHTML = `<p style="color:var(--color-notification, #f87171)">${parsed.error}</p>`;
            return;
          }
          if (parsed.chunk) {
            fullText += parsed.chunk;
            if (streamingEl) streamingEl.innerHTML = renderMarkdown(fullText);
          }
        } catch (_) {}
      }
    }

    // Restaurar botón con texto de éxito
    btn.innerHTML = "✅ Veredicto generado — pedir de nuevo";

    if (fullText.trim() && window._currentSnapshot) {
      const snap = { ...window._currentSnapshot, llm_analysis: fullText };
      window._currentSnapshot = snap;
      await saveAnalysisDataToDB(currentSport, currentPayload, snap);
    }
  } catch (e) {
    const streamingEl = document.getElementById("llm-streaming-text");
    if (streamingEl)
      streamingEl.innerHTML = `<p style="color:var(--color-notification, #f87171)">Error: ${e.message}</p>`;
    btn.innerHTML = "🔍 Reintentar Veredicto";
  } finally {
    btn.disabled = false;
    btn.style.opacity = "1";
  }
}

function toggleResultsModal() {
  const modal = document.getElementById("results-modal");
  if (!modal) return;
  modal.style.display = modal.style.display === "flex" ? "none" : "flex";
}

async function openResultsModal(id, matchTitle) {
  document.getElementById("results-analysis-id").value = id;
  document.getElementById("results-match-info").textContent = matchTitle;
  document.getElementById("results-form").reset();

  try {
    const resp = await fetch(`/api/v1/analysis/${id}`);
    if (resp.ok) {
      const data = await resp.json();
      // Populate fields if they exist
      document.getElementById("res-score-h").value =
        data.final_score_home ?? "";
      document.getElementById("res-score-a").value =
        data.final_score_away ?? "";
      document.getElementById("res-corners-h").value =
        data.final_corners_home ?? "";
      document.getElementById("res-corners-a").value =
        data.final_corners_away ?? "";
      document.getElementById("res-yellow-h").value =
        data.final_yellow_cards_home ?? "";
      document.getElementById("res-yellow-a").value =
        data.final_yellow_cards_away ?? "";
      document.getElementById("res-red-h").value =
        data.final_red_cards_home ?? "";
      document.getElementById("res-red-a").value =
        data.final_red_cards_away ?? "";
      document.getElementById("res-shots-h").value =
        data.final_shots_home ?? "";
      document.getElementById("res-shots-a").value =
        data.final_shots_away ?? "";
      document.getElementById("res-shots-target-h").value =
        data.final_shots_on_target_home ?? "";
      document.getElementById("res-shots-target-a").value =
        data.final_shots_on_target_away ?? "";
      document.getElementById("res-fouls-h").value =
        data.final_fouls_home ?? "";
      document.getElementById("res-fouls-a").value =
        data.final_fouls_away ?? "";
      document.getElementById("res-offsides-h").value =
        data.final_offsides_home ?? "";
      document.getElementById("res-offsides-a").value =
        data.final_offsides_away ?? "";
    }
  } catch (err) {
    console.error("Error loading results for editing:", err);
  }

  toggleResultsModal();
}

async function saveFinalResults(event) {
  event.preventDefault();
  const id = document.getElementById("results-analysis-id").value;

  const body = {
    final_score_home: toNullableNumber("res-score-h"),
    final_score_away: toNullableNumber("res-score-a"),
    final_corners_home: toNullableNumber("res-corners-h"),
    final_corners_away: toNullableNumber("res-corners-a"),
    final_yellow_cards_home: toNullableNumber("res-yellow-h"),
    final_yellow_cards_away: toNullableNumber("res-yellow-a"),
    final_red_cards_home: toNullableNumber("res-red-h"),
    final_red_cards_away: toNullableNumber("res-red-a"),
    final_shots_home: toNullableNumber("res-shots-h"),
    final_shots_away: toNullableNumber("res-shots-a"),
    final_shots_on_target_home: toNullableNumber("res-shots-target-h"),
    final_shots_on_target_away: toNullableNumber("res-shots-target-a"),
    final_fouls_home: toNullableNumber("res-fouls-h"),
    final_fouls_away: toNullableNumber("res-fouls-a"),
    final_offsides_home: toNullableNumber("res-offsides-h"),
    final_offsides_away: toNullableNumber("res-offsides-a"),
  };

  try {
    const res = await fetch(`/api/v1/analysis/${id}/results`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) throw new Error("Error al guardar resultados");

    const data = await res.json();
    const acc =
      data.accuracy_percentage != null
        ? data.accuracy_percentage.toFixed(1)
        : "0.0";
    toggleResultsModal();
    loadHistory(); // Recargar lista para ver el nuevo acierto
  } catch (e) {
    showError(e.message);
  }
}

async function toggleStatsModal() {
  const modal = document.getElementById("stats-modal");
  const isVisible = modal.style.display !== "none";

  if (!isVisible) {
    modal.style.display = "flex";
    await loadGlobalStats();
    await loadDetailedPicks();
  } else {
    modal.style.display = "none";
  }
}

function switchStatsTab(tabId) {
  document
    .querySelectorAll(".stats-tab-content")
    .forEach((c) => (c.style.display = "none"));
  document
    .querySelectorAll(".modal-tabs .tab-btn")
    .forEach((b) => b.classList.remove("active"));

  document.getElementById(`stats-tab-${tabId}`).style.display = "block";
  document.getElementById(`tab-btn-${tabId}`).classList.add("active");
}

let cachedGlobalStats = null;
let activeStatsCategory = "professional";

function switchStatsCategory(category) {
  activeStatsCategory = category;
  renderCategoryStats(category);
}

// Keep track of Chart instance to destroy old one when category changes
let profitChartInstance = null;

function renderCategoryStats(category) {
  if (!cachedGlobalStats) return;

  // Update active button classes in category selector
  document
    .querySelectorAll(".category-selector-container .tab-btn")
    .forEach((btn) => {
      if (btn.dataset.category === category) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });

  const data =
    cachedGlobalStats.category_stats &&
    cachedGlobalStats.category_stats[category]
      ? cachedGlobalStats.category_stats[category]
      : cachedGlobalStats; // fallback if category_stats not present

  // Tab General - Main stats cards
  document.getElementById("stat-total-picks").textContent = data.total_picks;
  document.getElementById("stat-total-hits").textContent = data.total_hits;
  document.getElementById("stat-total-misses").textContent =
    data.total_picks - data.total_hits;
  document.getElementById("stat-global-accuracy").textContent =
    `${data.accuracy !== undefined ? data.accuracy.toFixed(1) : (data.global_accuracy || 0).toFixed(1)}%`;
  document.getElementById("stat-total-pending").textContent =
    data.total_pending || 0;

  // Exact score stats population
  const exactPred = data.total_exact_scores_predicted || 0;
  const exactHits = data.total_exact_scores_hits || 0;
  const exactAcc = exactPred > 0 ? (exactHits / exactPred) * 100 : 0;

  const elExactPred = document.getElementById("stat-exact-predicted");
  const elExactHits = document.getElementById("stat-exact-hits");
  const elExactAcc = document.getElementById("stat-exact-accuracy");
  if (elExactPred) elExactPred.textContent = exactPred;
  if (elExactHits) elExactHits.textContent = exactHits;
  if (elExactAcc) elExactAcc.textContent = `${exactAcc.toFixed(1)}%`;

  // Tab Advanced - average odds
  document.getElementById("stat-avg-odds").textContent = (
    data.avg_odds || 0
  ).toFixed(2);
  document.getElementById("stat-avg-winning-odds").textContent = (
    data.avg_winning_odds || 0
  ).toFixed(2);

  // New Metrics Calculation (Yield and ROI)
  // Yield = (Net Profit / Total Investment) * 100
  // Net Profit = (Sum of odds of winning picks) - (Total resolved picks)
  // ROI = Net Profit (relative to 1 unit flat stake)
  // Category accuracy:
  const catAcc = data.accuracy !== undefined ? data.accuracy : 0;
  document.getElementById("stat-category-accuracy").textContent =
    `${catAcc.toFixed(1)}%`;

  let netProfit = 0;
  let totalStake = 0;

  // To compute Yield/ROI and chart correctly, we can use the cachedDetailedPicks
  let profitHistory = []; // list of {date, profit}

  if (window.cachedDetailedPicks) {
    // Filter picks for this category that have results (resolved)
    const categoryPicks = window.cachedDetailedPicks.filter((p) => {
      if (p.success === null) return false; // skip pending
      if (
        category === "professional" &&
        (p.is_underdog || p.is_high_confidence)
      )
        return false;
      if (category === "underdog" && !p.is_underdog) return false;
      if (category === "high_confidence" && !p.is_high_confidence) return false;
      return true;
    });

    // Sort chronologically (oldest first)
    categoryPicks.sort((a, b) => new Date(a.date) - new Date(b.date));

    // Calculate profit progression
    let cumulativeProfit = 0;
    categoryPicks.forEach((p) => {
      const odds = p.odds || 0;
      let profit = -1; // 1 unit lost by default
      if (p.success === true) {
        profit = odds - 1; // won odds - stake
      }
      cumulativeProfit += profit;
      totalStake += 1;

      const dateStr = new Date(p.date).toISOString().split("T")[0];
      profitHistory.push({ date: dateStr, profit: cumulativeProfit });
    });
    netProfit = cumulativeProfit;
  }

  const yieldValue = totalStake > 0 ? (netProfit / totalStake) * 100 : 0.0;

  // Format ROI text color based on positive/negative
  const roiEl = document.getElementById("stat-roi");
  roiEl.textContent = `${netProfit >= 0 ? "+" : ""}${netProfit.toFixed(2)} u`;
  roiEl.style.color = netProfit >= 0 ? "#22c55e" : "#ef4444";

  const yieldEl = document.getElementById("stat-yield");
  yieldEl.textContent = `${yieldValue >= 0 ? "+" : ""}${yieldValue.toFixed(1)}%`;
  yieldEl.style.color = yieldValue >= 0 ? "#3b82f6" : "#ef4444";

  // Render Profit Chart
  renderProfitChart(profitHistory);

  // Best/worst markets, leagues, teams
  const renderAnalytics = (containerId, items) => {
    const cont = document.getElementById(containerId);
    if (!cont) return;
    cont.innerHTML =
      !items || items.length === 0
        ? '<div style="opacity: 0.5; font-size: 0.8rem; padding: 1rem;">No hay datos suficientes</div>'
        : "";

    if (items) {
      items.forEach((item) => {
        const el = document.createElement("div");
        el.className = "analytics-item";

        const profitVal = item.profit ?? 0.0;
        const profitText =
          (profitVal >= 0 ? "+" : "") + profitVal.toFixed(2) + " u";
        const profitColor = profitVal >= 0 ? "#22c55e" : "#ef4444";

        el.innerHTML = `
            <div class="analytics-item__main">
                <span class="analytics-item__name">${item.name}</span>
                <span class="analytics-item__stat">${item.hits} aciertos de ${item.picks} picks | <strong style="color: ${profitColor}">${profitText}</strong></span>
            </div>
            <span class="analytics-item__acc">${item.accuracy.toFixed(0)}%</span>
        `;
        cont.appendChild(el);
      });
    }
  };
  renderAnalytics("best-markets-container", data.best_markets || []);
  renderAnalytics("best-leagues-container", data.best_leagues || []);
  renderAnalytics("best-teams-container", data.best_teams || []);

  // Buckets
  const renderBuckets = (containerId, items) => {
    const cont = document.getElementById(containerId);
    if (!cont) return;
    cont.innerHTML =
      !items || items.length === 0
        ? '<div style="opacity: 0.5; font-size: 0.8rem; padding: 1rem;">No hay datos suficientes</div>'
        : "";

    if (items) {
      items.forEach((item) => {
        const el = document.createElement("div");
        el.className = "analytics-item";
        el.innerHTML = `
            <div class="analytics-item__main">
                <span class="analytics-item__name">${item.bucket}</span>
                <span class="analytics-item__stat">Cuota prom: ${item.avg_odds.toFixed(2)} | ${item.count} picks</span>
            </div>
            <span class="analytics-item__acc" style="color: ${item.accuracy >= 60 ? "#22c55e" : item.accuracy >= 40 ? "#eab308" : "#ef4444"}">${item.accuracy.toFixed(0)}%</span>
        `;
        cont.appendChild(el);
      });
    }
  };

  renderBuckets("odds-buckets-container", data.odds_buckets || []);
  renderBuckets("edge-buckets-container", data.edge_buckets || []);
  renderBuckets("confidence-buckets-container", data.confidence_buckets || []);
}

function renderProfitChart(profitHistory) {
  const ctx = document.getElementById("profit-chart");
  if (!ctx) return;

  if (profitChartInstance) {
    profitChartInstance.destroy();
  }

  // Group by date to show only one point per day (last cumulative profit of that day)
  const groupedData = {};
  profitHistory.forEach((item) => {
    groupedData[item.date] = item.profit;
  });

  const labels = Object.keys(groupedData);
  const dataPoints = Object.values(groupedData);

  // If no data, show empty chart helper
  if (labels.length === 0) {
    labels.push("Sin datos");
    dataPoints.push(0);
  }

  profitChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Profit Acumulado (u)",
          data: dataPoints,
          borderColor: "#6366f1",
          backgroundColor: "rgba(99, 102, 241, 0.1)",
          borderWidth: 3,
          fill: true,
          tension: 0.3,
          pointBackgroundColor: "#8b5cf6",
          pointBorderColor: "#fff",
          pointHoverRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          backgroundColor: "#0f172a",
          titleColor: "#94a3b8",
          bodyColor: "#fff",
          borderColor: "rgba(255,255,255,0.1)",
          borderWidth: 1,
          callbacks: {
            label: function (context) {
              const val = context.parsed.y;
              return `Profit: ${val >= 0 ? "+" : ""}${val.toFixed(2)} u`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: {
            color: "rgba(255, 255, 255, 0.05)",
          },
          ticks: {
            color: "#94a3b8",
            font: {
              family: "Inter",
              size: 10,
            },
          },
        },
        y: {
          grid: {
            color: "rgba(255, 255, 255, 0.05)",
          },
          ticks: {
            color: "#94a3b8",
            font: {
              family: "Inter",
              size: 10,
            },
            callback: function (value) {
              return (value >= 0 ? "+" : "") + value + " u";
            },
          },
        },
      },
    },
  });
}

function getModalDateParams() {
  const range = document.getElementById("modal-date-range")
    ? document.getElementById("modal-date-range").value
    : "all";
  let dateFrom = "";
  let dateTo = "";

  if (range === "today") {
    const todayStr = new Date().toISOString().split("T")[0];
    dateFrom = `${todayStr}T00:00:00`;
    dateTo = `${todayStr}T23:59:59`;
  } else if (range === "7days") {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    dateFrom = d.toISOString().split("T")[0] + "T00:00:00";
  } else if (range === "30days") {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    dateFrom = d.toISOString().split("T")[0] + "T00:00:00";
  } else if (range === "custom") {
    const fromVal = document.getElementById("modal-date-from")
      ? document.getElementById("modal-date-from").value
      : "";
    const toVal = document.getElementById("modal-date-to")
      ? document.getElementById("modal-date-to").value
      : "";
    if (fromVal) dateFrom = `${fromVal}T00:00:00`;
    if (toVal) dateTo = `${toVal}T23:59:59`;
  }

  let params = [];
  if (dateFrom) params.push(`date_from=${encodeURIComponent(dateFrom)}`);
  if (dateTo) params.push(`date_to=${encodeURIComponent(dateTo)}`);
  return params.length > 0 ? "?" + params.join("&") : "";
}

function handleModalDateRangeChange() {
  const range = document.getElementById("modal-date-range").value;
  const customInputs = document.getElementById("modal-custom-date-inputs");
  if (customInputs) {
    customInputs.style.display = range === "custom" ? "flex" : "none";
  }
  reloadModalStats();
}

async function reloadModalStats() {
  await loadGlobalStats();
  await loadDetailedPicks();
}

async function loadGlobalStats() {
  try {
    const queryParams = getModalDateParams();
    const res = await fetch(`/api/v1/stats/global${queryParams}`);
    if (!res.ok) throw new Error("Error cargando estadísticas");
    const data = await res.json();
    cachedGlobalStats = data;

    // Render sport chips (which are global across categories)
    const container = document.getElementById("sport-stats-container");
    if (container) {
      container.innerHTML = "";
      if (data.sport_stats) {
        Object.entries(data.sport_stats).forEach(([sport, stats]) => {
          const chip = document.createElement("div");
          chip.style = `
            padding: 0.5rem 1rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            border-radius: 20px;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
          `;
          chip.innerHTML = `
            <span style="font-weight: 600; text-transform: uppercase;">${sport}:</span>
            <span style="color: var(--accent)">${stats.hits}/${stats.picks}</span>
            <small style="opacity: 0.7">(${stats.accuracy.toFixed(1)}%)</small>
          `;
          container.appendChild(chip);
        });
      }
    }

    // Render for the currently active category
    renderCategoryStats(activeStatsCategory);
  } catch (e) {
    showError(e.message);
  }
}

async function loadDetailedPicks() {
  const tbody = document.getElementById("picks-stats-list");
  tbody.innerHTML =
    '<tr><td colspan="8" style="text-align: center; padding: 2rem;">Cargando picks...</td></tr>';

  try {
    const queryParams = getModalDateParams();
    const separator = queryParams ? "&" : "?";
    const res = await fetch(
      `/api/v1/stats/picks${queryParams}${separator}limit=200`,
    );
    if (!res.ok) throw new Error("Error cargando picks");
    const picks = await res.json();
    window.cachedDetailedPicks = picks;

    // Reset filters
    const catSelect = document.getElementById("pick-filter-category");
    const resSelect = document.getElementById("pick-filter-result");
    if (catSelect) catSelect.value = "all";
    if (resSelect) resSelect.value = "all";

    filterDetailedPicksUI();
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--error); padding: 2rem;">${e.message}</td></tr>`;
  }
}

function filterDetailedPicksUI() {
  const tbody = document.getElementById("picks-stats-list");
  if (!window.cachedDetailedPicks) return;

  const catFilter = document.getElementById("pick-filter-category").value;
  const resFilter = document.getElementById("pick-filter-result").value;

  tbody.innerHTML = "";

  const filtered = window.cachedDetailedPicks.filter((p) => {
    // Filter by Category
    if (catFilter !== "all") {
      if (
        catFilter === "professional" &&
        (p.is_underdog || p.is_high_confidence)
      )
        return false;
      if (catFilter === "underdog" && !p.is_underdog) return false;
      if (catFilter === "high_confidence" && !p.is_high_confidence)
        return false;
    }

    // Filter by Result
    if (resFilter !== "all") {
      if (resFilter === "hit" && p.success !== true) return false;
      if (resFilter === "miss" && p.success !== false) return false;
      if (resFilter === "pending" && p.success !== null && p.success !== "void")
        return false;
      if (resFilter === "void" && p.success !== "void") return false;
    }

    return true;
  });

  if (filtered.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="8" style="text-align: center; padding: 2rem;">No hay picks que coincidan con los filtros.</td></tr>';
    return;
  }

  filtered.forEach((p) => {
    const tr = document.createElement("tr");
    tr.style.borderBottom = "1px solid rgba(255,255,255,0.05)";

    const dateStr = new Date(p.date).toLocaleDateString();
    const statusBadge =
      p.success === null
        ? '<span style="color: var(--text-dim)">⏳ Pendiente</span>'
        : p.success
          ? '<span style="color: #22c55e; font-weight: 600;">✅ Acierto</span>'
          : '<span style="color: #ef4444; font-weight: 600;">❌ Fallo</span>';

    const valueBadge = p.is_value
      ? '<span title="Value Pick" style="color: var(--accent); margin-right: 4px;">💎</span>'
      : "";

    const evVal = p.edge_ev !== null ? (p.edge_ev * 100).toFixed(1) : "N/A";
    const fairOdds = p.fair_odds !== null ? p.fair_odds.toFixed(2) : "N/A";
    const evColor =
      p.edge_ev > 0.07 ? "#22c55e" : p.edge_ev > 0.02 ? "#eab308" : "#ef4444";

    let catBadge = "";
    if (p.is_underdog) {
      catBadge =
        '<span class="value-line-card__badge badge--underdog" style="margin-top: 0; font-size: 0.65rem;">🦄 Underdog</span>';
    } else if (p.is_high_confidence) {
      catBadge =
        '<span class="value-line-card__badge badge--high" style="margin-top: 0; font-size: 0.65rem; background: rgba(245, 158, 11, 0.15); color: #f59e0b;">⭐ Alta Conf.</span>';
    } else {
      catBadge =
        '<span class="value-line-card__badge badge--strong" style="margin-top: 0; font-size: 0.65rem;">💼 Profesional</span>';
    }

    tr.innerHTML = `
      <td style="padding: 0.75rem; font-size: 0.85rem; color: var(--text-dim);">${dateStr}</td>
      <td style="padding: 0.75rem; vertical-align: middle;">${catBadge}</td>
      <td style="padding: 0.75rem; font-weight: 500;">
        <div style="font-size: 0.9rem;">${p.match_title}</div>
        <small style="text-transform: uppercase; opacity: 0.6; font-size: 0.7rem;">${p.sport}</small>
      </td>
      <td style="padding: 0.75rem;">
        ${valueBadge}<span style="font-weight: 600;">${p.selection}</span>
        <div style="font-size: 0.75rem; opacity: 0.7;">${p.market} ${p.line || ""}</div>
      </td>
      <td style="padding: 0.75rem; text-align: center; font-family: monospace;">${p.odds.toFixed(2)}</td>
      <td style="padding: 0.75rem; text-align: center; font-family: monospace; color: ${evColor}; font-weight: 600;">${evVal}%</td>
      <td style="padding: 0.75rem; text-align: center; font-family: monospace; color: var(--text-dim);">${fairOdds}</td>
      <td style="padding: 0.75rem; text-align: center;">${statusBadge}</td>
    `;
    tbody.appendChild(tr);
  });
}
