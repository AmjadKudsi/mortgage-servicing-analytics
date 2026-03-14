/* ═══════════════════════════════════════════
   ml-demo.js — ML Results Interactive Explorer
   Loads pre-computed JSON data from the ML pipeline
   and renders charts + tables using Plotly.js
   ═══════════════════════════════════════════ */

const DATA_DIR = 'data/';
const COLORS = {
    accent: '#C4973B',
    accentDim: '#8B6914',
    bg: '#141f2b',
    card: '#1a2735',
    border: '#243040',
    text: '#8a9bb0',
    textLight: '#e8e6e3',
    success: '#2ecc71',
    warning: '#f39c12',
    danger: '#e74c3c',
};

const PLOTLY_LAYOUT = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: '-apple-system, sans-serif', size: 12, color: COLORS.text },
    margin: { l: 50, r: 20, t: 10, b: 50 },
    xaxis: { gridcolor: COLORS.border, zerolinecolor: COLORS.border },
    yaxis: { gridcolor: COLORS.border, zerolinecolor: COLORS.border },
};

const PLOTLY_CONFIG = { responsive: true, displayModeBar: false };

// ── Load all data and render ──
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const [evalData, segData] = await Promise.all([
            fetch(DATA_DIR + 'evaluation.json').then(r => r.json()),
            fetch(DATA_DIR + 'risk_segments.json').then(r => r.json()),
        ]);

        renderOverview(evalData);
        renderFeatures(evalData);
        renderSegments(segData);
    } catch (err) {
        console.error('ML demo data load failed:', err);
        document.querySelector('.ml-demo').innerHTML +=
            '<p style="color: #e74c3c; padding: 16px;">Data files not found. Run: python3 python/export/portfolio_export.py</p>';
    }
});


function renderOverview(evalData) {
    // Find best Model B
    const modelB = evalData.model_b?.models || {};
    let best = null;
    let bestAuc = -1;
    for (const [name, metrics] of Object.entries(modelB)) {
        if (metrics.auc_roc > bestAuc) {
            bestAuc = metrics.auc_roc;
            best = metrics;
        }
    }

    if (!best) return;

    // KPIs
    document.getElementById('kpi-auc').textContent = best.auc_roc.toFixed(4);
    const lift10 = best.lift_analysis?.find(l => l.top_pct === 10);
    const lift20 = best.lift_analysis?.find(l => l.top_pct === 20);
    document.getElementById('kpi-lift10').textContent = lift10 ? lift10.capture_rate_pct + '%' : '—';
    document.getElementById('kpi-lift20').textContent = lift20 ? lift20.capture_rate_pct + '%' : '—';
    document.getElementById('kpi-segments').textContent = evalData.model_a?.total_segments || '—';

    // Lift chart
    const liftData = best.lift_analysis || [];
    if (liftData.length > 0) {
        const xVals = [0, ...liftData.map(l => l.top_pct)];
        const yVals = [0, ...liftData.map(l => l.capture_rate_pct)];

        Plotly.newPlot('lift-chart', [
            {
                x: xVals, y: yVals,
                type: 'scatter', mode: 'lines+markers',
                line: { color: COLORS.accent, width: 3 },
                marker: { size: 8, color: COLORS.accent },
                name: 'Model',
                hovertemplate: 'Top %{x}% of loans → catches %{y:.1f}% of delinquencies<extra></extra>',
            },
            {
                x: [0, 100], y: [0, 100],
                type: 'scatter', mode: 'lines',
                line: { color: COLORS.border, width: 1, dash: 'dash' },
                name: 'Random',
                hoverinfo: 'skip',
            }
        ], {
            ...PLOTLY_LAYOUT,
            height: 300,
            xaxis: { ...PLOTLY_LAYOUT.xaxis, title: '% of Loans Reviewed (ranked by risk score)', range: [0, 25] },
            yaxis: { ...PLOTLY_LAYOUT.yaxis, title: '% of Delinquencies Captured', range: [0, 100] },
            showlegend: true,
            legend: { x: 0.6, y: 0.3, font: { size: 11 }, bgcolor: 'rgba(0,0,0,0)' },
        }, PLOTLY_CONFIG);
    }
}


function renderFeatures(evalData) {
    const modelB = evalData.model_b?.models || {};
    let best = null;
    let bestAuc = -1;
    for (const [name, metrics] of Object.entries(modelB)) {
        if (metrics.auc_roc > bestAuc) {
            bestAuc = metrics.auc_roc;
            best = metrics;
        }
    }

    if (!best || !best.feature_importance) return;

    const features = best.feature_importance.slice(0, 10).reverse();
    const names = features.map(f => f.feature.replace(/_/g, ' ').replace(/credit score band /i, '').replace(/ltv bucket /i, '').replace(/rate bucket /i, ''));
    const values = features.map(f => f.importance);

    Plotly.newPlot('feature-chart', [{
        y: names,
        x: values,
        type: 'bar',
        orientation: 'h',
        marker: {
            color: values.map((v, i) => {
                const ratio = i / values.length;
                return `rgba(196, 151, 59, ${0.4 + ratio * 0.6})`;
            }),
        },
        hovertemplate: '%{y}: %{x:.4f}<extra></extra>',
    }], {
        ...PLOTLY_LAYOUT,
        height: 320,
        margin: { l: 180, r: 20, t: 10, b: 40 },
        xaxis: { ...PLOTLY_LAYOUT.xaxis, title: 'Feature Importance' },
        yaxis: { ...PLOTLY_LAYOUT.yaxis, automargin: true },
    }, PLOTLY_CONFIG);
}


function renderSegments(segments) {
    const tbody = document.getElementById('segments-body');
    if (!tbody || !segments.length) return;

    tbody.innerHTML = segments.slice(0, 15).map(seg => {
        const dlqClass = seg.actual_dlq_rate > 5 ? 'color: #e74c3c' :
                         seg.actual_dlq_rate > 2 ? 'color: #f39c12' : '';
        return `<tr>
            <td>${seg.credit_score_band}</td>
            <td>${seg.ltv_bucket}</td>
            <td>${seg.rate_bucket}</td>
            <td>${seg.orig_year}</td>
            <td style="text-align:right">${seg.loans.toLocaleString()}</td>
            <td style="text-align:right; color: ${COLORS.accent}">${seg.avg_risk_score}%</td>
            <td style="text-align:right; ${dlqClass}">${seg.actual_dlq_rate}%</td>
        </tr>`;
    }).join('');
}
