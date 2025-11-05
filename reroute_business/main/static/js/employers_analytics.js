(function(){
  function parseJSON(id){ try{ const el=document.getElementById(id); return el ? JSON.parse(el.textContent||'{}') : {}; } catch(_){ return {}; } }
  const data = parseJSON('emp-analytics-data');
  function init(){
    if (typeof Plotly==='undefined') return;
    const baseLayout = { margin: { l: 40, r:20, t:20, b:40 }, paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)' };
    const baseConfig = { displayModeBar: 'hover', responsive: true, scrollZoom: true };
    const apj = data.applications_per_job || { labels: [], data: [] };
    try { Plotly.newPlot('appsPerJob', [{ type:'bar', x: apj.labels, y: apj.data, marker:{ color:'#2563eb' } }], { ...baseLayout, xaxis:{ automargin:true }, yaxis:{ gridcolor:'rgba(0,0,0,0.05)' } }, baseConfig); } catch(_){ }
    const aot = data.applications_over_time || { labels: [], data: [] };
    try { Plotly.newPlot('appsOverTime', [{ type:'scatter', mode:'lines', x: aot.labels, y: aot.data, line:{ color:'#16a34a' }, fill:'tozeroy', fillcolor:'rgba(22,163,74,0.15)' }], { ...baseLayout, hovermode:'x unified' }, baseConfig); } catch(_){ }
    const sb = data.status_breakdown || { labels: [], data: [] };
    try { Plotly.newPlot('statusBreakdown', [{ type:'pie', labels: sb.labels, values: sb.data, textinfo:'label+percent', hoverinfo:'label+value+percent', marker:{ colors:['#2563eb','#22c1dc','#16a34a','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#94a3b8'] } }], { ...baseLayout }, baseConfig); } catch(_){ }
  }
  document.addEventListener('DOMContentLoaded', function(){
    var sel = document.getElementById('time_range');
    if (sel && sel.form) sel.addEventListener('change', function(){ sel.form.submit(); });
    init();
  });
})();

