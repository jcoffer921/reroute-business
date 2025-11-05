(function(){
  function parseJSON(id){ try{ const el=document.getElementById(id); return el ? JSON.parse(el.textContent||'{}') : {}; } catch(_){ return {}; } }
  const data = parseJSON('analytics-events-data');
  if (typeof Plotly==='undefined') return;
  const colors = ['#2563eb','#22c1dc','#16a34a','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#94a3b8'];
  const baseLayout = { margin: { l: 30, r: 20, t: 20, b: 30 }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)' };
  const baseConfig = { displayModeBar: 'hover', responsive: true, scrollZoom: true };
  // Pie
  try { Plotly.newPlot('pageViewsPie', [{ type:'pie', labels:data.pieLabels||[], values:data.pieCounts||[], textinfo:'label+percent', hoverinfo:'label+value+percent', marker:{ colors } }], { ...baseLayout, showlegend:true, legend:{ orientation:'v', x:1, y:0.5 } }, baseConfig); } catch(_){ }
  // Line
  try { Plotly.newPlot('pageViewsLine', [{ type:'scatter', mode:'lines', name:'Page Views', x:data.lineLabels||[], y:data.lineCounts||[], line:{ color:'#2563eb' }, fill:'tozeroy', fillcolor:'rgba(37,99,235,0.2)' }], { ...baseLayout, hovermode:'x unified' }, baseConfig); } catch(_){ }
  // Stacked
  try { Plotly.newPlot('viewsStacked', [ { type:'bar', name:'Authenticated', x:data.lineLabels||[], y:data.authed||[], marker:{ color:'#16a34a' } }, { type:'bar', name:'Anonymous', x:data.lineLabels||[], y:data.anon||[], marker:{ color:'#94a3b8' } } ], { ...baseLayout, barmode:'stack' }, baseConfig); } catch(_){ }
  // Submit select on change
  document.addEventListener('DOMContentLoaded', function(){ const sel=document.getElementById('days'); if(sel){ sel.addEventListener('change', function(){ this.form && this.form.submit(); }); } });
})();

