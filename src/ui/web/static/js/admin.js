/**
 * Sherlock Admin Panel Client Javascript.
 * Handles dynamic UI rendering, filters state, Chart.js integrations, and server API calls.
 */

document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('admin-view-root');
  if (!root) return;

  const activeTab = root.getAttribute('data-active-tab') || 'dashboard';
  initAdminView(activeTab);
});

// State object
const adminState = {
  activeTab: 'dashboard',
  filters: {
    date_range: '',
    date_from: '',
    date_to: '',
    competition: '',
    market: '',
    category: '',
    bookmaker: '',
    status: '',
    count_in_profitability: '',
    is_blacklisted: '',
    is_value: '',
    is_publishable: '',
    is_underdog: '',
    filter_correlated: 'true',
    search: '',
    page: 1,
    page_size: 50,
    sort_by: 'match_date',
    sort_dir: 'desc',
    min_sample: 10,
    group_by: 'competition',
  },
  dbExplorer: {
    selectedTable: 'analysis_history',
    page: 1,
    page_size: 50,
    search: '',
    sort_by: '',
    sort_dir: 'desc',
  }
};

let chartInstances = {};

function initAdminView(tab) {
  adminState.activeTab = tab;
  parseUrlParams();

  if (tab === 'dashboard') {
    if (document.getElementById('dashboard-content') || document.getElementById('loader')) {
      return;
    }
    renderDashboardView();
  } else if (tab === 'picks') {
    renderPicksView();
  } else if (tab === 'stats') {
    renderStatsView();
  } else if (tab === 'database') {
    renderDatabaseView();
  }
}

function parseUrlParams() {
  const params = new URLSearchParams(window.location.search);
  for (const [key, val] of params.entries()) {
    if (key in adminState.filters) {
      adminState.filters[key] = val;
    }
  }
}

function syncUrlParams() {
  const params = new URLSearchParams();
  for (const [key, val] of Object.entries(adminState.filters)) {
    if (val !== '' && val !== null && val !== undefined) {
      params.set(key, val);
    }
  }
  const newUrl = `${window.location.pathname}?${params.toString()}`;
  window.history.replaceState({}, '', newUrl);
}

// ---------------------------------------------------------------------------
// TAB 1: Dashboard View
// ---------------------------------------------------------------------------

async function renderDashboardView() {
  const root = document.getElementById('admin-view-root');
  root.innerHTML = `
    ${renderFiltersBarHtml()}
    <div id="dashboard-content">
      <div style="text-align: center; padding: 3rem; color: #94a3b8;">Cargando métricas del dashboard...</div>
    </div>
  `;
  bindFiltersBarEvents(() => renderDashboardView());

  try {
    const query = buildFilterQueryString();
    const resp = await fetch(`/api/v1/admin/dashboard/summary?${query}`);
    if (!resp.ok) throw new Error('Error al cargar datos del dashboard');
    const data = await resp.json();

    const container = document.getElementById('dashboard-content');
    container.innerHTML = `
      <!-- KPIs Grid -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-title">Picks Resueltos</div>
          <div class="kpi-value">${data.kpis.picks_resolved}</div>
          <div class="kpi-subtext">Pendientes: ${data.kpis.picks_pending}</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-title">Hit Rate (Acierto)</div>
          <div class="kpi-value ${data.kpis.hit_rate >= 50 ? 'positive' : 'negative'}">${data.kpis.hit_rate}%</div>
          <div class="kpi-subtext">Ganados: ${data.kpis.picks_won} | Perdidos: ${data.kpis.picks_lost}</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-title">ROI / Yield</div>
          <div class="kpi-value ${data.kpis.roi >= 0 ? 'positive' : 'negative'}">${data.kpis.roi}%</div>
          <div class="kpi-subtext">Unidades apostadas: ${data.kpis.units_staked} u</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-title">Beneficio Neto</div>
          <div class="kpi-value ${data.kpis.net_profit >= 0 ? 'positive' : 'negative'}">${data.kpis.net_profit > 0 ? '+' : ''}${data.kpis.net_profit} u</div>
          <div class="kpi-subtext">Push: ${data.kpis.picks_push} | Void: ${data.kpis.picks_void}</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-title">Cuota Promedio</div>
          <div class="kpi-value">${data.kpis.avg_odds}</div>
          <div class="kpi-subtext">Cuota Ganadora: ${data.kpis.avg_winning_odds}</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-title">Break-Even Rate</div>
          <div class="kpi-value">${data.kpis.break_even_rate}%</div>
          <div class="kpi-subtext">Acierto mínimo requerido</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-title">Edge Promedio</div>
          <div class="kpi-value positive">+${(data.kpis.avg_edge * 100).toFixed(1)}%</div>
          <div class="kpi-subtext">Kelly Promedio: ${(data.kpis.avg_kelly * 100).toFixed(1)}%</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-title">Rendimiento Ajustado (Stake 1)</div>
          <div class="kpi-value ${data.kpis.yield_rate_adjusted >= 0 ? 'positive' : 'negative'}">${data.kpis.yield_rate_adjusted}%</div>
          <div class="kpi-subtext">Beneficio Adj: ${data.kpis.net_profit_adjusted > 0 ? '+' : ''}${data.kpis.net_profit_adjusted} u | CLV: ${data.kpis.avg_clv !== null && data.kpis.avg_clv !== undefined ? (data.kpis.avg_clv > 0 ? '+' : '') + data.kpis.avg_clv + '%' : 'N/A'}</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-title">Total Análisis</div>
          <div class="kpi-value">${data.kpis.total_analyses}</div>
          <div class="kpi-subtext">Total picks: ${data.kpis.total_picks}</div>
        </div>
      </div>

      <!-- Quality Metrics & Calibration -->
      <div style="background: var(--admin-card-bg); border: 1px solid var(--admin-border); border-radius: 0.75rem; padding: 1.25rem; margin-bottom: 2rem;">
        <h3 class="chart-title">🎯 Calidad del Modelo & Calibración de Probabilidades</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
          <div><span style="color:#94a3b8; font-size:0.8rem;">PROB. MODELO MEDIA:</span> <strong>${data.quality.avg_model_prob}%</strong></div>
          <div><span style="color:#94a3b8; font-size:0.8rem;">PROB. IMPLÍCITA MEDIA:</span> <strong>${data.quality.avg_implied_prob}%</strong></div>
          <div><span style="color:#94a3b8; font-size:0.8rem;">DIFERENCIA ACIERTO REAL:</span> <strong style="color: ${data.quality.actual_vs_expected_diff >= 0 ? '#34d399' : '#f87171'};">${data.quality.actual_vs_expected_diff > 0 ? '+' : ''}${data.quality.actual_vs_expected_diff}%</strong></div>
          <div><span style="color:#94a3b8; font-size:0.8rem;">BRIER SCORE:</span> <strong>${data.quality.brier_score !== null ? data.quality.brier_score : 'N/A'}</strong></div>
        </div>
        
        <table class="admin-table" style="margin-top: 0.5rem;">
          <thead>
            <tr>
              <th>Banda Probabilidad Modelo</th>
              <th>Picks Resueltos</th>
              <th>Prob. Modelo Promedio</th>
              <th>Acierto Real</th>
              <th>Desviación (Calibración)</th>
            </tr>
          </thead>
          <tbody>
            ${data.quality.calibration_bands.map(b => `
              <tr>
                <td><strong>${b.band}</strong></td>
                <td>${b.total_picks}</td>
                <td>${b.avg_model_prob}%</td>
                <td>${b.actual_hit_rate}%</td>
                <td style="color: ${b.diff >= 0 ? '#34d399' : '#f87171'}; font-weight:700;">${b.diff > 0 ? '+' : ''}${b.diff}%</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>

      <!-- Charts Grid -->
      <div class="charts-grid">
        <div class="chart-card">
          <div class="chart-title">📈 Curva de Beneficio Acumulado (Diaria)</div>
          <canvas id="chart-cumulative-yield" height="220"></canvas>
        </div>
        <div class="chart-card">
          <div class="chart-title">🏆 ROI por Competición / Liga</div>
          <canvas id="chart-roi-league" height="220"></canvas>
        </div>
        <div class="chart-card">
          <div class="chart-title">🎯 ROI por Mercado de Apuestas</div>
          <canvas id="chart-roi-market" height="220"></canvas>
        </div>
        <div class="chart-card">
          <div class="chart-title">📊 Rendimiento por Rango de Cuota</div>
          <canvas id="chart-perf-odds" height="220"></canvas>
        </div>
      </div>
    `;

    renderDashboardCharts(data.charts);
  } catch (err) {
    document.getElementById('dashboard-content').innerHTML = `
      <div class="warning-banner">Error al cargar dashboard: ${err.message}</div>
    `;
  }
}

function renderDashboardCharts(chartsData) {
  // Destroy existing charts
  Object.values(chartInstances).forEach(c => c && c.destroy());
  chartInstances = {};

  // 1. Cumulative Yield Chart
  const ctxCum = document.getElementById('chart-cumulative-yield');
  if (ctxCum && chartsData.cumulative_yield.length > 0) {
    chartInstances.cum = new Chart(ctxCum, {
      type: 'line',
      data: {
        labels: chartsData.cumulative_yield.map(p => p.date),
        datasets: [{
          label: 'Unidades Acumuladas',
          data: chartsData.cumulative_yield.map(p => p.cumulative_profit),
          borderColor: '#6366f1',
          backgroundColor: 'rgba(99, 102, 241, 0.1)',
          fill: true,
          tension: 0.3,
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#94a3b8' } },
          y: { ticks: { color: '#94a3b8' } }
        }
      }
    });
  }

  // 2. ROI by League
  const ctxLeague = document.getElementById('chart-roi-league');
  if (ctxLeague && chartsData.roi_by_league.length > 0) {
    chartInstances.league = new Chart(ctxLeague, {
      type: 'bar',
      data: {
        labels: chartsData.roi_by_league.slice(0, 8).map(p => p.label),
        datasets: [{
          label: 'ROI %',
          data: chartsData.roi_by_league.slice(0, 8).map(p => p.value),
          backgroundColor: chartsData.roi_by_league.slice(0, 8).map(p => p.value >= 0 ? '#10b981' : '#ef4444'),
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { x: { ticks: { color: '#94a3b8' } }, y: { ticks: { color: '#94a3b8' } } }
      }
    });
  }

  // 3. ROI by Market
  const ctxMarket = document.getElementById('chart-roi-market');
  if (ctxMarket && chartsData.roi_by_market.length > 0) {
    chartInstances.market = new Chart(ctxMarket, {
      type: 'bar',
      data: {
        labels: chartsData.roi_by_market.map(p => p.label),
        datasets: [{
          label: 'ROI %',
          data: chartsData.roi_by_market.map(p => p.value),
          backgroundColor: chartsData.roi_by_market.map(p => p.value >= 0 ? '#38bdf8' : '#f87171'),
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { x: { ticks: { color: '#94a3b8' } }, y: { ticks: { color: '#94a3b8' } } }
      }
    });
  }

  // 4. Performance by Odds Range
  const ctxOdds = document.getElementById('chart-perf-odds');
  if (ctxOdds && chartsData.performance_by_odds_range.length > 0) {
    chartInstances.odds = new Chart(ctxOdds, {
      type: 'bar',
      data: {
        labels: chartsData.performance_by_odds_range.map(p => p.label),
        datasets: [{
          label: 'ROI %',
          data: chartsData.performance_by_odds_range.map(p => p.value),
          backgroundColor: '#818cf8',
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { x: { ticks: { color: '#94a3b8' } }, y: { ticks: { color: '#94a3b8' } } }
      }
    });
  }
}

// ---------------------------------------------------------------------------
// TAB 2: Picks Explorer View
// ---------------------------------------------------------------------------

async function renderPicksView() {
  const root = document.getElementById('admin-view-root');
  root.innerHTML = `
    ${renderFiltersBarHtml(true)}
    <div id="picks-content">
      <div style="text-align: center; padding: 3rem; color: #94a3b8;">Cargando picks históricos...</div>
    </div>
  `;
  bindFiltersBarEvents(() => renderPicksView());

  try {
    const query = buildFilterQueryString();
    const resp = await fetch(`/api/v1/admin/picks?${query}`);
    if (!resp.ok) throw new Error('Error al consultar picks');
    const data = await resp.json();

    const container = document.getElementById('picks-content');

    if (data.pagination.warning) {
      container.innerHTML = `<div class="warning-banner">${data.pagination.warning}</div>`;
    } else {
      container.innerHTML = '';
    }

    container.innerHTML += `
      <div class="table-container">
        <table class="admin-table">
          <thead>
            <tr>
              <th onclick="setSort('match_date')">Fecha ⇕</th>
              <th onclick="setSort('match_title')">Partido ⇕</th>
              <th onclick="setSort('competition')">Liga ⇕</th>
              <th>Mercado</th>
              <th>Selección</th>
              <th>Estado</th>
              <th>Categoría</th>
              <th>Cuota</th>
              <th>Prob. Modelo</th>
              <th>Prob. Calibrada</th>
              <th>Edge</th>
              <th>Kelly</th>
              <th onclick="setSort('stake_units')">Stake ⇕</th>
              <th>Beneficio</th>
              <th>ROI</th>
              <th onclick="setSort('bookmaker')">Bookmaker ⇕</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            ${data.picks.map(p => `
              <tr style="cursor: pointer;" onclick="openPickDetail('${p.id}')">
                <td>${formatDate(p.match_date)}</td>
                <td><strong>${escapeHtml(p.match_title)}</strong></td>
                <td>${escapeHtml(p.competition || '')}</td>
                <td>${escapeHtml(p.market)}</td>
                <td><span style="color:#38bdf8; font-weight:600;">${escapeHtml(p.selection)}</span></td>
                <td><span class="badge badge-${p.status}">${p.status}</span></td>
                <td><span class="badge ${p.category === 'Underdog' ? 'badge-push' : 'badge-won'}">${escapeHtml(p.category || 'Profesional')}</span></td>
                <td>${p.odds}</td>
                <td>${(p.model_prob * 100).toFixed(1)}%</td>
                <td style="color:#a7f3d0;">${p.calibrated_prob ? (p.calibrated_prob * 100).toFixed(1) + '%' : '-'}</td>
                <td style="color:${p.edge >= 0 ? '#34d399' : '#f87171'};">+${(p.edge * 100).toFixed(1)}%</td>
                <td>${(p.kelly * 100).toFixed(1)}%</td>
                <td>${p.stake} u</td>
                <td style="font-weight:700; color:${p.profit > 0 ? '#34d399' : (p.profit < 0 ? '#f87171' : '#cbd5e1')};">
                  ${p.profit > 0 ? '+' : ''}${p.profit} u
                </td>
                <td>${p.roi !== null ? p.roi + '%' : '-'}</td>
                <td>${escapeHtml(p.bookmaker || '')}</td>
                <td onclick="event.stopPropagation();">
                  <button class="btn-admin btn-secondary" onclick="openEditOperationalModal('${p.analysis_id}')">⚙️ Editar</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      ${renderPaginationHtml(data.pagination)}
    `;
  } catch (err) {
    document.getElementById('picks-content').innerHTML = `
      <div class="warning-banner">Error al consultar picks: ${err.message}</div>
    `;
  }
}

async function openPickDetail(pickId) {
  try {
    const resp = await fetch(`/api/v1/admin/picks/${pickId}`);
    if (!resp.ok) throw new Error('No se pudo cargar el detalle del pick.');
    const data = await resp.json();

    const titleEl = document.getElementById('modal-title');
    const bodyEl = document.getElementById('modal-body');

    titleEl.innerText = `Audit Pick: ${data.analysis.match_title}`;
    bodyEl.innerHTML = `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
        <div>
          <h4 style="color:#38bdf8; margin-bottom:0.5rem;">ℹ️ Información del Pick</h4>
          <p><strong>Liga:</strong> ${data.analysis.competition}</p>
          <p><strong>Mercado:</strong> ${data.pick.market} | <strong>Selección:</strong> ${data.pick.selection}</p>
          <p><strong>Cuota Tomada:</strong> ${data.pick.odds} | <strong>Bookmaker:</strong> ${data.analysis.bookmaker}</p>
          <p><strong>Probabilidad Modelo:</strong> ${(data.pick.model_prob * 100).toFixed(1)}% | <strong>Prob. Implícita:</strong> ${(data.pick.implied_prob * 100).toFixed(1)}%</p>
          <p><strong>Edge Calculado:</strong> +${(data.pick.edge * 100).toFixed(1)}% | <strong>Kelly Recomendado:</strong> ${(data.pick.kelly * 100).toFixed(1)}%</p>
          <p><strong>Stake Aplicado:</strong> ${data.pick.stake} u | <strong>Beneficio Final:</strong> ${data.pick.profit} u</p>
        </div>
        <div>
          <h4 style="color:#818cf8; margin-bottom:0.5rem;">📊 Contexto Predictivo</h4>
          <p><strong>xG Predicho Local:</strong> ${data.predictive_context.expected_goals_home || 'N/A'}</p>
          <p><strong>xG Predicho Visitante:</strong> ${data.predictive_context.expected_goals_away || 'N/A'}</p>
          <p><strong>Rentabilidad:</strong> ${data.analysis.count_in_profitability ? 'Incluido' : 'Excluido'}</p>
          <p><strong>Marcado para Recálculo:</strong> ${data.analysis.needs_recalc ? 'Sí' : 'No'}</p>
        </div>
      </div>

      <div style="margin-top:1.5rem; background:#0f172a; padding:1rem; border-radius:0.5rem; border:1px solid #334155;">
        <h4 style="color:#f59e0b; margin-bottom:0.4rem;">🔎 Auditoría Final del Partido</h4>
        <p style="font-size:0.9rem; color:#e2e8f0; line-height:1.4;">${data.post_match_audit.audit_explanation}</p>
      </div>

      <div style="margin-top:1.5rem; display:flex; gap:1rem;">
        <button class="btn-admin" onclick="triggerMarkRecalculation('${data.analysis.id}')">🔄 Marcar para Recálculo</button>
        <button class="btn-admin btn-secondary" onclick="closeAdminModal()">Cerrar</button>
      </div>
    `;

    document.getElementById('admin-modal').classList.add('show');
  } catch (err) {
    alert(err.message);
  }
}

async function triggerMarkRecalculation(analysisId) {
  try {
    const resp = await fetch(`/api/v1/admin/picks/${analysisId}/mark-for-recalculation`, { method: 'POST' });
    if (!resp.ok) throw new Error('Falló el recálculo');
    alert('Pick marcado para recálculo exitosamente.');
    closeAdminModal();
    renderPicksView();
  } catch (err) {
    alert(err.message);
  }
}

function openEditOperationalModal(analysisId) {
  const titleEl = document.getElementById('modal-title');
  const bodyEl = document.getElementById('modal-body');

  titleEl.innerText = 'Editar Campos Operativos Autorizados';
  bodyEl.innerHTML = `
    <form id="edit-op-form" onsubmit="submitOperationalEdit(event, '${analysisId}')">
      <div class="filter-group" style="margin-bottom:1rem;">
        <label class="filter-label">Liga / Competición</label>
        <input type="text" id="op-comp" class="filter-input" placeholder="Nombre de competición" style="width:100%;">
      </div>
      <div class="filter-group" style="margin-bottom:1rem;">
        <label class="filter-label">Casa de Apuestas Principal</label>
        <input type="text" id="op-bookie" class="filter-input" placeholder="Nombre de bookmaker" style="width:100%;">
      </div>
      <div class="filter-group" style="margin-bottom:1rem;">
        <label class="filter-label">Stake Unidades</label>
        <input type="number" step="0.1" id="op-stake" class="filter-input" placeholder="1.0" style="width:100%;">
      </div>
      <div class="filter-group" style="margin-bottom:1rem;">
        <label class="filter-label">Incluir en Rentabilidad Global</label>
        <select id="op-profit" class="filter-select" style="width:100%;">
          <option value="true">Sí (Incluir)</option>
          <option value="false">No (Excluir)</option>
        </select>
      </div>
      <div style="display:flex; gap:1rem; margin-top:1.5rem;">
        <button type="submit" class="btn-admin">Guardar Cambios</button>
        <button type="button" class="btn-admin btn-secondary" onclick="closeAdminModal()">Cancelar</button>
      </div>
    </form>
  `;
  document.getElementById('admin-modal').classList.add('show');
}

async function submitOperationalEdit(event, analysisId) {
  event.preventDefault();
  const comp = document.getElementById('op-comp').value.trim();
  const bookie = document.getElementById('op-bookie').value.trim();
  const stakeVal = document.getElementById('op-stake').value;
  const profVal = document.getElementById('op-profit').value === 'true';

  const payload = {};
  if (comp) payload.competition = comp;
  if (bookie) payload.bookmaker = bookie;
  if (stakeVal) payload.stake_units = parseFloat(stakeVal);
  payload.count_in_profitability = profVal;

  try {
    const resp = await fetch(`/api/v1/admin/picks/${analysisId}/operational-fields`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error('Error al actualizar campos.');
    alert('Campos operativos actualizados.');
    closeAdminModal();
    if (adminState.activeTab === 'picks') renderPicksView();
  } catch (err) {
    alert(err.message);
  }
}

// ---------------------------------------------------------------------------
// TAB 3: Advanced Stats View
// ---------------------------------------------------------------------------

async function renderStatsView() {
  const root = document.getElementById('admin-view-root');
  root.innerHTML = `
    <div class="filters-bar">
      <div class="filter-group">
        <label class="filter-label">Agrupar Estadísticas Por</label>
        <select id="stat-group-by" class="filter-select" onchange="adminState.filters.group_by=this.value; renderStatsView();">
          <option value="competition" ${adminState.filters.group_by==='competition'?'selected':''}>Liga / Competición</option>
          <option value="market" ${adminState.filters.group_by==='market'?'selected':''}>Mercado</option>
          <option value="category" ${adminState.filters.group_by==='category'?'selected':''}>Categoría Pick</option>
          <option value="bookmaker" ${adminState.filters.group_by==='bookmaker'?'selected':''}>Casa de Apuestas</option>
          <option value="odds_range" ${adminState.filters.group_by==='odds_range'?'selected':''}>Rango de Cuota</option>
          <option value="edge_range" ${adminState.filters.group_by==='edge_range'?'selected':''}>Rango de Edge</option>
        </select>
      </div>
      <div class="filter-group">
        <label class="filter-label">Muestra Mínima (Picks)</label>
        <input type="number" class="filter-input" value="${adminState.filters.min_sample}" min="1" onchange="adminState.filters.min_sample=parseInt(this.value)||1; renderStatsView();">
      </div>
      <div class="filter-group" style="margin-left: auto; align-self: flex-end;">
        <button class="btn-admin" onclick="triggerExport('csv')">📥 Exportar CSV</button>
        <button class="btn-admin btn-secondary" onclick="triggerExport('excel')">📊 Exportar Excel</button>
      </div>
    </div>

    <div id="stats-content">
      <div style="text-align: center; padding: 3rem; color: #94a3b8;">Cargando segmentaciones...</div>
    </div>
  `;

  try {
    const resp = await fetch(`/api/v1/admin/stats/grouped?group_by=${adminState.filters.group_by}&min_sample=${adminState.filters.min_sample}`);
    if (!resp.ok) throw new Error('Error al consultar estadísticas.');
    const data = await resp.json();

    const container = document.getElementById('stats-content');
    container.innerHTML = `
      <div class="table-container">
        <table class="admin-table">
          <thead>
            <tr>
              <th>Segmento (${data.group_by})</th>
              <th>Picks Totales</th>
              <th>Resueltos</th>
              <th>Ganados</th>
              <th>Perdidos</th>
              <th>Hit Rate %</th>
              <th>Cuota Prom.</th>
              <th>Stake Total</th>
              <th>Beneficio Neto</th>
              <th>ROI %</th>
              <th>Break-Even %</th>
              <th>Edge Prom.</th>
              <th>Max Drawdown</th>
              <th>Racha Pérdidas</th>
            </tr>
          </thead>
          <tbody>
            ${data.items.map(i => `
              <tr>
                <td><strong>${escapeHtml(i.segment_name)}</strong></td>
                <td>${i.total_picks}</td>
                <td>${i.resolved_picks}</td>
                <td>${i.won_picks}</td>
                <td>${i.lost_picks}</td>
                <td><strong style="color:${i.hit_rate>=50?'#34d399':'#f87171'};">${i.hit_rate}%</strong></td>
                <td>${i.avg_odds}</td>
                <td>${i.total_stake} u</td>
                <td style="font-weight:700; color:${i.net_profit>=0?'#34d399':'#f87171'};">${i.net_profit > 0 ? '+' : ''}${i.net_profit} u</td>
                <td><strong style="color:${i.roi>=0?'#34d399':'#f87171'};">${i.roi}%</strong></td>
                <td>${i.break_even_rate}%</td>
                <td>+${(i.avg_edge).toFixed(2)}%</td>
                <td style="color:#f87171;">-${i.max_drawdown} u</td>
                <td>${i.max_losing_streak}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (err) {
    document.getElementById('stats-content').innerHTML = `
      <div class="warning-banner">Error: ${err.message}</div>
    `;
  }
}

function triggerExport(fmt) {
  window.open(`/api/v1/admin/stats/export?export_format=${fmt}&group_by=${adminState.filters.group_by}`, '_blank');
}

// ---------------------------------------------------------------------------
// TAB 4: Database Explorer View
// ---------------------------------------------------------------------------

async function renderDatabaseView() {
  const root = document.getElementById('admin-view-root');
  root.innerHTML = `
    <div style="margin-bottom:1.5rem; display:flex; gap:1rem; align-items:center;">
      <h3 style="margin:0;">🗄️ Explorador Controlado de Base de Datos</h3>
      <span style="font-size:0.8rem; color:#94a3b8; background:#0f172a; padding:0.3rem 0.6rem; border-radius:0.4rem; border:1px solid #334155;">
        🔒 Consultas mediante Lista Blanca
      </span>
    </div>
    
    <div id="db-tables-list" style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:1rem; margin-bottom:1.5rem;">
      <!-- Table Selector Cards -->
    </div>

    <div id="db-content">
      <div style="text-align: center; padding: 3rem; color: #94a3b8;">Cargando tablas...</div>
    </div>
  `;

  try {
    const respTables = await fetch('/api/v1/admin/database/tables');
    const tables = await respTables.json();

    const listEl = document.getElementById('db-tables-list');
    listEl.innerHTML = tables.map(t => `
      <div class="kpi-card" style="cursor:pointer; border-color:${adminState.dbExplorer.selectedTable===t.name?'#6366f1':'var(--admin-border)'}" onclick="selectDbTable('${t.name}')">
        <div class="kpi-title">${t.name}</div>
        <div class="kpi-value" style="font-size:1.3rem;">${t.approx_rows} reg</div>
        <div class="kpi-subtext">${t.columns_count} columnas</div>
      </div>
    `).join('');

    loadDbTableRows();
  } catch (err) {
    document.getElementById('db-content').innerHTML = `<div class="warning-banner">Error: ${err.message}</div>`;
  }
}

function selectDbTable(tblName) {
  adminState.dbExplorer.selectedTable = tblName;
  adminState.dbExplorer.page = 1;
  renderDatabaseView();
}

async function loadDbTableRows() {
  const tbl = adminState.dbExplorer.selectedTable;
  const container = document.getElementById('db-content');

  try {
    const searchVal = adminState.dbExplorer.search || '';
    const sortBy = adminState.dbExplorer.sort_by || '';
    const sortDir = adminState.dbExplorer.sort_dir || 'desc';

    const resp = await fetch(`/api/v1/admin/database/tables/${tbl}/rows?page=${adminState.dbExplorer.page}&page_size=${adminState.dbExplorer.page_size}&search=${encodeURIComponent(searchVal)}&sort_by=${encodeURIComponent(sortBy)}&sort_dir=${encodeURIComponent(sortDir)}`);
    const data = await resp.json();

    container.innerHTML = `
      <div style="margin-bottom:1rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
        <h4 style="margin:0;">Tabla: <code>${tbl}</code> (${data.pagination.total_records} registros totales)</h4>
        <div style="display:flex; gap:0.5rem; align-items:center;">
          <input type="text" class="filter-input" placeholder="Buscar en ${tbl}..." value="${escapeHtml(searchVal)}" oninput="onDbSearchInput(this.value)" style="min-width:220px;">
        </div>
      </div>
      
      <div class="table-container">
        <table class="admin-table">
          <thead>
            <tr>
              <th style="position: sticky; left: 0; z-index: 10; background: #0f172a;">Acciones</th>
              ${data.columns.map(c => `
                <th onclick="setDbSort('${c.name}')" title="Ordenar por ${c.name}">
                  ${c.name} ${c.primary_key ? '🔑' : ''} ${sortBy === c.name ? (sortDir === 'asc' ? '▲' : '▼') : '⇕'}
                </th>
              `).join('')}
            </tr>
          </thead>
          <tbody>
            ${data.rows.map(row => {
              const recId = row.id || row[data.columns[0].name];
              return `
                <tr style="cursor: pointer;" onclick="editDbRow('${tbl}', '${recId}')">
                  <td style="position: sticky; left: 0; background: #1e293b; z-index: 5;" onclick="event.stopPropagation();">
                    <button class="btn-admin btn-secondary" onclick="editDbRow('${tbl}', '${recId}')">✏️ Editar</button>
                  </td>
                  ${data.columns.map(c => `
                    <td>${formatCellVal(row[c.name])}</td>
                  `).join('')}
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
      
      <div class="pagination-bar">
        <div>Página ${data.pagination.page} de ${data.pagination.total_pages} (${data.pagination.total_records} registros)</div>
        <div class="pagination-controls">
          <button class="btn-admin btn-secondary" ${!data.pagination.has_prev ? 'disabled' : ''} onclick="adminState.dbExplorer.page--; loadDbTableRows();">◀ Anteriores</button>
          <button class="btn-admin btn-secondary" ${!data.pagination.has_next ? 'disabled' : ''} onclick="adminState.dbExplorer.page++; loadDbTableRows();">Siguientes ▶</button>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="warning-banner">Error al cargar registros: ${err.message}</div>`;
  }
}

let dbSearchDebounceTimer;
function onDbSearchInput(val) {
  clearTimeout(dbSearchDebounceTimer);
  dbSearchDebounceTimer = setTimeout(() => {
    adminState.dbExplorer.search = val;
    adminState.dbExplorer.page = 1;
    loadDbTableRows();
  }, 400);
}

function setDbSort(col) {
  if (adminState.dbExplorer.sort_by === col) {
    adminState.dbExplorer.sort_dir = adminState.dbExplorer.sort_dir === 'asc' ? 'desc' : 'asc';
  } else {
    adminState.dbExplorer.sort_by = col;
    adminState.dbExplorer.sort_dir = 'asc';
  }
  loadDbTableRows();
}

async function editDbRow(tblName, recordId) {
  try {
    const respSchema = await fetch(`/api/v1/admin/database/tables/${tblName}/schema`);
    if (!respSchema.ok) throw new Error('Error al obtener esquema de tabla');
    const schema = await respSchema.json();

    const editableCols = schema.columns.filter(c => c.description === 'Editable');
    if (editableCols.length === 0) {
      alert(`La tabla '${tblName}' es de solo lectura o no tiene campos editables autorizados.`);
      return;
    }

    const titleEl = document.getElementById('modal-title');
    const bodyEl = document.getElementById('modal-body');

    titleEl.innerText = `Editar Registro #${recordId} (${tblName})`;
    bodyEl.innerHTML = `
      <form id="edit-db-form" onsubmit="submitDbRowEdit(event, '${tblName}', '${recordId}')">
        <p style="color:#94a3b8; font-size:0.85rem; margin-bottom:1rem;">
          Modificando campos operativos autorizados para la tabla <code>${tblName}</code>.
        </p>
        ${editableCols.map(c => `
          <div class="filter-group" style="margin-bottom:1rem;">
            <label class="filter-label">${c.name} (${c.type})</label>
            ${c.type.toLowerCase().includes('bool') ? `
              <select id="db-field-${c.name}" class="filter-select" style="width:100%;">
                <option value="true">True (Sí)</option>
                <option value="false">False (No)</option>
              </select>
            ` : (c.name.toLowerCase().includes('date') || c.name.toLowerCase().includes('time') || c.type.toLowerCase().includes('date') || c.type.toLowerCase().includes('time') ? `
              <input type="text" id="db-field-${c.name}" class="filter-input" placeholder="2026-08-27T06:18:37.071785" style="width:100%;">
            ` : `
              <input type="${c.type.toLowerCase().includes('int') || c.type.toLowerCase().includes('float') || c.type.toLowerCase().includes('numeric') ? 'number' : 'text'}" 
                     step="any" id="db-field-${c.name}" class="filter-input" placeholder="Nuevo valor para ${c.name}" style="width:100%;">
            `)}
          </div>
        `).join('')}
        <div style="display:flex; gap:1rem; margin-top:1.5rem;">
          <button type="submit" class="btn-admin">Guardar Cambios</button>
          <button type="button" class="btn-admin btn-secondary" onclick="closeAdminModal()">Cancelar</button>
        </div>
      </form>
    `;

    document.getElementById('admin-modal').classList.add('show');
  } catch (err) {
    alert(err.message);
  }
}

async function submitDbRowEdit(event, tblName, recordId) {
  event.preventDefault();
  try {
    const respSchema = await fetch(`/api/v1/admin/database/tables/${tblName}/schema`);
    const schema = await respSchema.json();
    const editableCols = schema.columns.filter(c => c.description === 'Editable');

    const updates = {};
    for (const c of editableCols) {
      const inputEl = document.getElementById(`db-field-${c.name}`);
      if (!inputEl) continue;
      const valStr = inputEl.value.trim();
      if (valStr === '') continue;

      if (c.type.toLowerCase().includes('bool')) {
        updates[c.name] = valStr === 'true';
      } else if (c.type.toLowerCase().includes('int')) {
        updates[c.name] = parseInt(valStr, 10);
      } else if (c.type.toLowerCase().includes('float') || c.type.toLowerCase().includes('numeric')) {
        updates[c.name] = parseFloat(valStr);
      } else {
        updates[c.name] = valStr;
      }
    }

    if (Object.keys(updates).length === 0) {
      alert('No ingresaste ningún cambio.');
      return;
    }

    const resp = await fetch(`/api/v1/admin/database/tables/${tblName}/rows/${recordId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ updates }),
    });

    if (!resp.ok) {
      const errData = await resp.json();
      throw new Error(errData.detail || 'Error al actualizar el registro.');
    }

    alert('Registro actualizado exitosamente.');
    closeAdminModal();
    loadDbTableRows();
  } catch (err) {
    alert(err.message);
  }
}

// ---------------------------------------------------------------------------
// Helpers & Components
// ---------------------------------------------------------------------------

function triggerPicksExport(fmt) {
  const query = buildFilterQueryString();
  window.open(`/api/v1/admin/picks/export?export_format=${fmt}&${query}`, '_blank');
}

function renderFiltersBarHtml(includeSearch = false) {
  return `
    <div class="filters-bar">
      ${includeSearch ? `
        <div class="filter-group">
          <label class="filter-label">Búsqueda Libre</label>
          <input type="text" class="filter-input" placeholder="Equipo, Liga..." value="${adminState.filters.search}" oninput="adminState.filters.search=this.value; debounceSearch();">
        </div>
      ` : ''}
      <div class="filter-group">
        <label class="filter-label">Rango Fecha</label>
        <select class="filter-select" onchange="adminState.filters.date_range=this.value; onFilterChange();">
          <option value="">Todo el historial</option>
          <option value="today" ${adminState.filters.date_range==='today'?'selected':''}>Hoy</option>
          <option value="3d" ${adminState.filters.date_range==='3d'?'selected':''}>Últimos 3 días</option>
          <option value="7d" ${adminState.filters.date_range==='7d'?'selected':''}>Últimos 7 días</option>
          <option value="30d" ${adminState.filters.date_range==='30d'?'selected':''}>Últimos 30 días</option>
        </select>
      </div>
      <div class="filter-group">
        <label class="filter-label">Competición / Liga</label>
        <input type="text" class="filter-input" placeholder="Filtrar liga..." value="${adminState.filters.competition}" onchange="adminState.filters.competition=this.value; onFilterChange();">
      </div>
      <div class="filter-group">
        <label class="filter-label">Estado</label>
        <select class="filter-select" onchange="adminState.filters.status=this.value; onFilterChange();">
          <option value="">Todos los estados</option>
          <option value="won" ${adminState.filters.status==='won'?'selected':''}>Ganado</option>
          <option value="lost" ${adminState.filters.status==='lost'?'selected':''}>Perdido</option>
          <option value="push" ${adminState.filters.status==='push'?'selected':''}>Nulo / Push</option>
          <option value="pending" ${adminState.filters.status==='pending'?'selected':''}>Pendiente</option>
        </select>
      </div>
      <div class="filter-group">
        <label class="filter-label">Rentabilidad</label>
        <select class="filter-select" onchange="adminState.filters.count_in_profitability=this.value; onFilterChange();">
          <option value="">Todos</option>
          <option value="true" ${adminState.filters.count_in_profitability==='true'?'selected':''}>Incluido en Rentabilidad</option>
          <option value="false" ${adminState.filters.count_in_profitability==='false'?'selected':''}>Excluido</option>
        </select>
      </div>
      <div class="filter-group">
        <label class="filter-label">Lista Negra</label>
        <select class="filter-select" onchange="adminState.filters.is_blacklisted=this.value; onFilterChange();">
          <option value="">Todos</option>
          <option value="false" ${adminState.filters.is_blacklisted==='false'?'selected':''}>Sin Lista Negra</option>
          <option value="true" ${adminState.filters.is_blacklisted==='true'?'selected':''}>Solo Blacklisted</option>
        </select>
      </div>
      ${includeSearch ? `
        <div class="filter-group">
          <label class="filter-label">Correlacionados</label>
          <select class="filter-select" onchange="adminState.filters.filter_correlated=this.value; onFilterChange();">
            <option value="true" ${adminState.filters.filter_correlated==='true'?'selected':''}>Ocultar correlacionados</option>
            <option value="false" ${adminState.filters.filter_correlated==='false'?'selected':''}>Mostrar todos</option>
          </select>
        </div>
        <div class="filter-group" style="margin-left: auto; align-self: flex-end;">
          <button class="btn-admin" onclick="triggerPicksExport('csv')">📥 Exportar CSV</button>
          <button class="btn-admin btn-secondary" onclick="triggerPicksExport('excel')">📊 Exportar Excel</button>
        </div>
      ` : ''}
    </div>
  `;
}

function bindFiltersBarEvents(callback) {
  window.onFilterChange = () => {
    syncUrlParams();
    callback();
  };

  let debounceTimer;
  window.debounceSearch = () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      onFilterChange();
    }, 400);
  };
}

function buildFilterQueryString() {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(adminState.filters)) {
    if (v !== '' && v !== null && v !== undefined) params.set(k, v);
  }
  return params.toString();
}

function renderPaginationHtml(meta) {
  return `
    <div class="pagination-bar">
      <div>Mostrando página ${meta.page} de ${meta.total_pages} (${meta.total_records} registros)</div>
      <div class="pagination-controls">
        <button class="btn-admin btn-secondary" ${!meta.has_prev ? 'disabled' : ''} onclick="adminState.filters.page--; onFilterChange();">◀ Anteriores</button>
        <button class="btn-admin btn-secondary" ${!meta.has_next ? 'disabled' : ''} onclick="adminState.filters.page++; onFilterChange();">Siguientes ▶</button>
      </div>
    </div>
  `;
}

function setSort(col) {
  if (adminState.filters.sort_by === col) {
    adminState.filters.sort_dir = adminState.filters.sort_dir === 'asc' ? 'desc' : 'asc';
  } else {
    adminState.filters.sort_by = col;
    adminState.filters.sort_dir = 'asc';
  }
  if (window.onFilterChange) window.onFilterChange();
}

function closeAdminModal() {
  document.getElementById('admin-modal').classList.remove('show');
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatDate(dtStr) {
  if (!dtStr) return '-';
  try {
    const d = new Date(dtStr);
    return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    return dtStr;
  }
}

function formatCellVal(val) {
  if (val === null || val === undefined) return '<span style="color:#64748b;">NULL</span>';
  if (typeof val === 'object') {
    const jsonStr = JSON.stringify(val);
    const shortStr = jsonStr.length > 35 ? jsonStr.substring(0, 35) + '...' : jsonStr;
    return `<span style="font-family:monospace; color:#38bdf8; max-width:250px; display:inline-block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(jsonStr)}">${escapeHtml(shortStr)}</span>`;
  }
  const strVal = String(val);
  if (strVal.length > 40) {
    return `<span title="${escapeHtml(strVal)}">${escapeHtml(strVal.substring(0, 40))}...</span>`;
  }
  return escapeHtml(strVal);
}
