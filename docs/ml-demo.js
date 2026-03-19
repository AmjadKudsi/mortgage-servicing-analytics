/* ml-demo.js v5 — red random line, theme aware */
const DATA_DIR = 'data/';
function getCC() {
    const s = getComputedStyle(document.documentElement);
    return { accent: s.getPropertyValue('--accent').trim()||'#C4973B', grid: s.getPropertyValue('--chart-grid').trim()||'rgba(36,48,64,0.3)', text: s.getPropertyValue('--chart-text').trim()||'#6a7d90', border: s.getPropertyValue('--border').trim()||'#243040' };
}
function mkL(c, extra) {
    return { paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)', font:{family:'-apple-system,sans-serif',size:13,color:c.text}, margin:{l:50,r:20,t:10,b:50}, xaxis:{gridcolor:c.grid,zerolinecolor:c.grid,gridwidth:1}, yaxis:{gridcolor:c.grid,zerolinecolor:c.grid,gridwidth:1}, ...extra };
}
const CFG={responsive:true,displayModeBar:false};
let _e=null,_s=null;
document.addEventListener('DOMContentLoaded',async()=>{
    try{[_e,_s]=await Promise.all([fetch(DATA_DIR+'evaluation.json').then(r=>r.json()),fetch(DATA_DIR+'risk_segments.json').then(r=>r.json())]);renderAll();}catch(e){console.error('ML data:',e);}
});
window.replotCharts=function(){if(_e)renderAll();};
function renderAll(){rO(_e);rF(_e);rS(_s);}
function gB(e){const m=e.model_b?.models||{};let b=null,a=-1;for(const v of Object.values(m)){if(v.auc_roc>a){a=v.auc_roc;b=v;}}return b;}
function rO(e){
    const b=gB(e);if(!b)return;const c=getCC();
    document.getElementById('kpi-auc').textContent=b.auc_roc.toFixed(4);
    const l10=b.lift_analysis?.find(l=>l.top_pct===10),l20=b.lift_analysis?.find(l=>l.top_pct===20);
    document.getElementById('kpi-lift10').textContent=l10?l10.capture_rate_pct+'%':'—';
    document.getElementById('kpi-lift20').textContent=l20?l20.capture_rate_pct+'%':'—';
    document.getElementById('kpi-segments').textContent=e.model_a?.total_segments||'—';
    const ld=b.lift_analysis||[];
    if(ld.length){
        Plotly.newPlot('lift-chart',[
            {x:[0,...ld.map(l=>l.top_pct)],y:[0,...ld.map(l=>l.capture_rate_pct)],type:'scatter',mode:'lines+markers',line:{color:c.accent,width:3},marker:{size:9,color:c.accent},name:'OriginRisk Model',hovertemplate:'Top %{x}% → catches %{y:.1f}%<extra></extra>'},
            {x:[0,100],y:[0,100],type:'scatter',mode:'lines',line:{color:'#e74c3c',width:2,dash:'dash'},name:'Random Baseline',hoverinfo:'skip'}
        ],mkL(c,{height:340,xaxis:{gridcolor:c.grid,zerolinecolor:c.grid,title:'% of Loans Reviewed (ranked by risk score)',range:[0,25]},yaxis:{gridcolor:c.grid,zerolinecolor:c.grid,title:'% Delinquencies Captured',range:[0,100]},showlegend:true,legend:{x:0.55,y:0.35,font:{size:12},bgcolor:'rgba(0,0,0,0)'}}),CFG);
    }
}
function rF(e){
    const b=gB(e);if(!b?.feature_importance)return;const c=getCC();
    const f=b.feature_importance.slice(0,10).reverse();
    const n=f.map(x=>x.feature.replace(/_/g,' ').replace(/credit score band /i,'').replace(/ltv bucket /i,'').replace(/rate bucket /i,''));
    const v=f.map(x=>x.importance);
    Plotly.newPlot('feature-chart',[{y:n,x:v,type:'bar',orientation:'h',marker:{color:v.map((_,i)=>{const r=i/v.length;return `rgba(196,151,59,${0.35+r*0.65})`;})},hovertemplate:'%{y}: %{x:.4f}<extra></extra>'}],mkL(c,{height:360,margin:{l:200,r:20,t:10,b:40},xaxis:{gridcolor:c.grid,zerolinecolor:c.grid,title:'Feature Importance'},yaxis:{gridcolor:c.grid,zerolinecolor:c.grid,automargin:true}}),CFG);
}
function rS(segs){
    const tb=document.getElementById('segments-body');if(!tb||!segs?.length)return;const c=getCC();
    tb.innerHTML=segs.slice(0,15).map(s=>{
        const d=s.actual_dlq_rate>5?'color:#e74c3c;font-weight:600':s.actual_dlq_rate>2?'color:#f39c12':'';
        return `<tr><td>${s.credit_score_band}</td><td>${s.ltv_bucket}</td><td>${s.rate_bucket}</td><td>${s.orig_year}</td><td style="text-align:right">${s.loans.toLocaleString()}</td><td style="text-align:right;color:${c.accent};font-weight:600">${s.avg_risk_score}%</td><td style="text-align:right;${d}">${s.actual_dlq_rate}%</td></tr>`;
    }).join('');
}
