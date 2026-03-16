/* ml-demo.js v4 — reads theme from CSS vars for chart colors */
const DATA_DIR = 'data/';

function getChartColors() {
    const s = getComputedStyle(document.documentElement);
    return {
        accent: s.getPropertyValue('--accent').trim() || '#C4973B',
        grid: s.getPropertyValue('--chart-grid').trim() || 'rgba(36,48,64,0.3)',
        text: s.getPropertyValue('--chart-text').trim() || '#6a7d90',
        border: s.getPropertyValue('--border').trim() || '#243040',
    };
}

function makeLayout(c, extra) {
    return {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { family: '-apple-system, sans-serif', size: 13, color: c.text },
        margin: { l: 50, r: 20, t: 10, b: 50 },
        xaxis: { gridcolor: c.grid, zerolinecolor: c.grid, gridwidth: 1 },
        yaxis: { gridcolor: c.grid, zerolinecolor: c.grid, gridwidth: 1 },
        ...extra
    };
}

const CFG = { responsive: true, displayModeBar: false };
let _evalData = null, _segData = null;

document.addEventListener('DOMContentLoaded', async () => {
    try {
        [_evalData, _segData] = await Promise.all([
            fetch(DATA_DIR + 'evaluation.json').then(r => r.json()),
            fetch(DATA_DIR + 'risk_segments.json').then(r => r.json()),
        ]);
        renderAll();
    } catch (e) { console.error('ML data load failed:', e); }
});

window.replotCharts = function() { if (_evalData) renderAll(); };

function renderAll() {
    renderOverview(_evalData);
    renderFeatures(_evalData);
    renderSegments(_segData);
}

function getBestModelB(evalData) {
    const models = evalData.model_b?.models || {};
    let best = null, bestAuc = -1;
    for (const m of Object.values(models)) { if (m.auc_roc > bestAuc) { bestAuc = m.auc_roc; best = m; } }
    return best;
}

function renderOverview(evalData) {
    const best = getBestModelB(evalData);
    if (!best) return;
    const c = getChartColors();

    document.getElementById('kpi-auc').textContent = best.auc_roc.toFixed(4);
    const l10 = best.lift_analysis?.find(l => l.top_pct === 10);
    const l20 = best.lift_analysis?.find(l => l.top_pct === 20);
    document.getElementById('kpi-lift10').textContent = l10 ? l10.capture_rate_pct + '%' : '—';
    document.getElementById('kpi-lift20').textContent = l20 ? l20.capture_rate_pct + '%' : '—';
    document.getElementById('kpi-segments').textContent = evalData.model_a?.total_segments || '—';

    const ld = best.lift_analysis || [];
    if (ld.length) {
        Plotly.newPlot('lift-chart', [
            { x: [0, ...ld.map(l => l.top_pct)], y: [0, ...ld.map(l => l.capture_rate_pct)], type: 'scatter', mode: 'lines+markers', line: { color: c.accent, width: 3 }, marker: { size: 9, color: c.accent }, name: 'Model', hovertemplate: 'Top %{x}% → catches %{y:.1f}%<extra></extra>' },
            { x: [0, 100], y: [0, 100], type: 'scatter', mode: 'lines', line: { color: c.grid, width: 1, dash: 'dash' }, name: 'Random', hoverinfo: 'skip' }
        ], makeLayout(c, {
            height: 340,
            xaxis: { gridcolor: c.grid, zerolinecolor: c.grid, title: '% of Loans Reviewed', range: [0, 25] },
            yaxis: { gridcolor: c.grid, zerolinecolor: c.grid, title: '% Delinquencies Captured', range: [0, 100] },
            showlegend: true, legend: { x: 0.6, y: 0.3, font: { size: 12 }, bgcolor: 'rgba(0,0,0,0)' }
        }), CFG);
    }
}

function renderFeatures(evalData) {
    const best = getBestModelB(evalData);
    if (!best?.feature_importance) return;
    const c = getChartColors();
    const feats = best.feature_importance.slice(0, 10).reverse();
    const names = feats.map(f => f.feature.replace(/_/g, ' ').replace(/credit score band /i, '').replace(/ltv bucket /i, '').replace(/rate bucket /i, ''));
    const vals = feats.map(f => f.importance);

    Plotly.newPlot('feature-chart', [{
        y: names, x: vals, type: 'bar', orientation: 'h',
        marker: { color: vals.map((v, i) => { const r = i / vals.length; return `rgba(196,151,59,${0.35 + r * 0.65})`; }) },
        hovertemplate: '%{y}: %{x:.4f}<extra></extra>'
    }], makeLayout(c, {
        height: 360, margin: { l: 200, r: 20, t: 10, b: 40 },
        xaxis: { gridcolor: c.grid, zerolinecolor: c.grid, title: 'Feature Importance' },
        yaxis: { gridcolor: c.grid, zerolinecolor: c.grid, automargin: true }
    }), CFG);
}

function renderSegments(segments) {
    const tbody = document.getElementById('segments-body');
    if (!tbody || !segments?.length) return;
    const c = getChartColors();
    tbody.innerHTML = segments.slice(0, 15).map(s => {
        const dlq = s.actual_dlq_rate > 5 ? 'color:#e74c3c;font-weight:600' : s.actual_dlq_rate > 2 ? 'color:#f39c12' : '';
        return `<tr><td>${s.credit_score_band}</td><td>${s.ltv_bucket}</td><td>${s.rate_bucket}</td><td>${s.orig_year}</td><td style="text-align:right">${s.loans.toLocaleString()}</td><td style="text-align:right;color:${c.accent};font-weight:600">${s.avg_risk_score}%</td><td style="text-align:right;${dlq}">${s.actual_dlq_rate}%</td></tr>`;
    }).join('');
}
