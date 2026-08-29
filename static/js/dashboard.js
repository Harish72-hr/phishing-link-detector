const chart = document.getElementById('riskChart');
if (chart) {
  const levels = JSON.parse(chart.dataset.levels);
  new Chart(chart, {type:'doughnut', data:{labels:['Phishing','Legitimate'],datasets:[{data:[chart.dataset.phishing,chart.dataset.legitimate],backgroundColor:['#ff8a5b','#b9f6d0'],borderWidth:0}]}, options:{plugins:{legend:{labels:{color:'#eef7f1'}}}}});
}
const levelChart = document.getElementById('levelChart');
if (levelChart) {
  const levels = JSON.parse(levelChart.dataset.levels);
  new Chart(levelChart, {type:'bar', data:{labels:Object.keys(levels),datasets:[{label:'Scans',data:Object.values(levels),backgroundColor:['#ff6b6b','#ff9f43','#ffd166','#b9f6d0']}]}, options:{scales:{x:{ticks:{color:'#91a5a8'}},y:{beginAtZero:true,ticks:{color:'#91a5a8'}}},plugins:{legend:{display:false}}}});
}
