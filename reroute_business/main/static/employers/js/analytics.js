// Employer Analytics — Chart.js + AJAX updater
(function () {
  const $ = (sel, root = document) => root.querySelector(sel);
  const overlay = $('#loadingOverlay');
  const timeSelect = $('#timeRange');
  const endpoint = (window.ANALYTICS_ENDPOINT || window.location.pathname);
  const bootstrap = (window.ANALYTICS_BOOTSTRAP || {});

  // Show/hide loading overlay
  function setLoading(active) {
    if (!overlay) return;
    overlay.classList.toggle('active', !!active);
    overlay.setAttribute('aria-hidden', active ? 'false' : 'true');
  }

  // Build charts
  let chartPerJob, chartOverTime, chartStatus;
  function initCharts() {
    const ctx1 = $('#chartPerJob');
    const ctx2 = $('#chartOverTime');
    const ctx3 = $('#chartStatus');
    if (!ctx1 || !ctx2 || !ctx3 || !window.Chart) return;

    chartPerJob = new Chart(ctx1, {
      type: 'bar',
      data: {
        labels: bootstrap.applications_per_job?.labels || [],
        datasets: [{
          label: 'Applications',
          data: bootstrap.applications_per_job?.data || [],
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.25)'
        }]
      },
      options: { responsive: true, maintainAspectRatio: true, aspectRatio: 2 }
    });

    chartOverTime = new Chart(ctx2, {
      type: 'line',
      data: {
        labels: bootstrap.applications_over_time?.labels || [],
        datasets: [{
          label: 'Applications',
          data: bootstrap.applications_over_time?.data || [],
          fill: false,
          borderColor: '#10b981',
          tension: 0.25,
          pointRadius: 2
        }]
      },
      options: { responsive: true, maintainAspectRatio: true, aspectRatio: 2 }
    });

    chartStatus = new Chart(ctx3, {
      type: 'pie',
      data: {
        labels: bootstrap.status_breakdown?.labels || [],
        datasets: [{
          label: 'Status',
          data: bootstrap.status_breakdown?.data || [],
          backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
        }]
      },
      options: { responsive: true, maintainAspectRatio: true, aspectRatio: 1 }
    });
  }

  function updateCharts(payload) {
    if (chartPerJob && payload.applications_per_job) {
      chartPerJob.data.labels = payload.applications_per_job.labels;
      chartPerJob.data.datasets[0].data = payload.applications_per_job.data;
      chartPerJob.update();
    }
    if (chartOverTime && payload.applications_over_time) {
      chartOverTime.data.labels = payload.applications_over_time.labels;
      chartOverTime.data.datasets[0].data = payload.applications_over_time.data;
      chartOverTime.update();
    }
    if (chartStatus && payload.status_breakdown) {
      chartStatus.data.labels = payload.status_breakdown.labels;
      chartStatus.data.datasets[0].data = payload.status_breakdown.data;
      chartStatus.update();
    }
  }

  async function fetchData(range) {
    const url = new URL(endpoint, window.location.origin);
    url.searchParams.set('time_range', range);
    const resp = await fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    if (!resp.ok) throw new Error('Network error');
    return resp.json();
  }

  // Events
  if (timeSelect) {
    timeSelect.addEventListener('change', async () => {
      setLoading(true);
      try {
        const range = timeSelect.value;
        const data = await fetchData(range);
        if (data && data.ok) {
          updateCharts(data);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    });
  }

  // Boot
  document.addEventListener('DOMContentLoaded', initCharts);
})();
