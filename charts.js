/* Shared Chart.js theme + helpers (dark dashboard) */
Chart.defaults.color = '#9fb3d9';
Chart.defaults.font.family = '"Inter", system-ui, sans-serif';
Chart.defaults.borderColor = 'rgba(80,110,170,.18)';
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.boxWidth = 8;
Chart.defaults.plugins.tooltip.backgroundColor = '#0b1430';
Chart.defaults.plugins.tooltip.borderColor = '#2a3d6b';
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.padding = 10;
const RR = {
  sev: {Minor:'#22c55e', Serious:'#f59e0b', Fatal:'#ef4444'},
  pal: ['#5b8cff','#22d3ee','#7c5cff','#f59e0b','#22c55e','#ef4444','#ec4899','#14b8a6','#a3e635'],
  make(id, cfg) { const el = document.getElementById(id); return el ? new Chart(el, cfg) : null; },
  stacked(id, labels, rows, type) {
    type = type || 'bar';
    return RR.make(id, {type, data:{labels, datasets:['Minor','Serious','Fatal'].map(s => ({label:s, data:rows.map(r=>r[s.toLowerCase()]),
      backgroundColor: type==='bar' ? RR.sev[s] : RR.sev[s]+'22', borderColor:RR.sev[s], borderWidth:2, tension:.35, fill:type!=='bar', borderRadius:type==='bar'?4:0, pointRadius:3}))},
      options:{responsive:true, maintainAspectRatio:false, interaction:{mode:'index', intersect:false},
        scales:{x:{stacked:type==='bar', grid:{display:false}}, y:{stacked:type==='bar', beginAtZero:true}}}});
  },
  hbar(id, labels, values, color) {
    return RR.make(id, {type:'bar', data:{labels, datasets:[{data:values, backgroundColor:color||'#5b8cff', borderRadius:6}]},
      options:{indexAxis:'y', responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}}, scales:{x:{beginAtZero:true}, y:{grid:{display:false}}}}});
  },
  vbar(id, labels, values, color) {
    return RR.make(id, {type:'bar', data:{labels, datasets:[{data:values, backgroundColor:color||'#5b8cff', borderRadius:6}]},
      options:{responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}}, scales:{x:{grid:{display:false}}, y:{beginAtZero:true}}}});
  },
  doughnut(id, labels, values) {
    return RR.make(id, {type:'doughnut', data:{labels, datasets:[{data:values, backgroundColor:RR.pal, borderColor:'#0f1832', borderWidth:3}]},
      options:{responsive:true, maintainAspectRatio:false, cutout:'66%', plugins:{legend:{position:'bottom'}}}});
  }
};
// mobile sidebar toggle
document.addEventListener('DOMContentLoaded', () => {
  const b = document.getElementById('menuBtn'), s = document.getElementById('sidebar');
  if (b && s) { b.addEventListener('click', () => s.classList.toggle('open')); document.querySelector('.main').addEventListener('click', () => s.classList.remove('open')); }
});
