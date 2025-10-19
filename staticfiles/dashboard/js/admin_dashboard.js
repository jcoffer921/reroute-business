// Admin dashboard charts (Plotly.js) + carousel + modal confirmations
document.addEventListener("DOMContentLoaded", () => {
  const {
    dates = [],
    usersByDay = [],
    jobsByDay = [],
    applicationsByDay = [],
    employersByDay = []
  } = window.dashboardData || {};

  const baseLayout = {
    margin: { l: 40, r: 20, t: 20, b: 40 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    xaxis: { showgrid: false },
    yaxis: { gridcolor: 'rgba(0,0,0,0.05)' },
    hovermode: 'x unified',
    showlegend: true,
  };
  const baseConfig = { displayModeBar: 'hover', responsive: true, scrollZoom: true };

  // Plot helpers
  function plotLine(id, name, x, y, color, fillcolor) {
    const el = document.getElementById(id);
    if (!el) return null;
    Plotly.newPlot(el, [
      { type: 'scatter', mode: 'lines', name, x, y, line: { color }, fill: 'tozeroy', fillcolor }
    ], { ...baseLayout }, baseConfig);
    return el;
  }

  // Charts
  const usersEl = plotLine('usersChart', 'New Users', dates, usersByDay, '#0d6efd', 'rgba(13,110,253,0.15)');
  const jobsEl = plotLine('jobsChart', 'New Jobs', dates, jobsByDay, '#198754', 'rgba(25,135,84,0.15)');
  const appsEl = (Array.isArray(applicationsByDay) && applicationsByDay.length)
    ? plotLine('applicationsChart', 'New Applications', dates, applicationsByDay, '#fd7e14', 'rgba(253,126,20,0.15)')
    : null;
  const empsEl = (Array.isArray(employersByDay) && employersByDay.length)
    ? plotLine('employersChart', 'New Employers', dates, employersByDay, '#17a2b8', 'rgba(23,162,184,0.15)')
    : null;

  // Remove slides without data
  document.querySelectorAll('.charts-carousel__slide').forEach(slide => {
    const div = slide.querySelector('.plotly-chart');
    const id = div ? div.id : '';
    const hasChart = (
      (id === 'applicationsChart' && Array.isArray(applicationsByDay) && applicationsByDay.length) ||
      (id === 'employersChart' && Array.isArray(employersByDay) && employersByDay.length) ||
      (id === 'usersChart' || id === 'jobsChart')
    );
    if (!hasChart) slide.remove();
  });

  // Accessible carousel
  const carousel = document.querySelector('.charts-carousel');
  if (carousel) {
    const track = carousel.querySelector('.charts-carousel__track');
    let slides = Array.from(carousel.querySelectorAll('.charts-carousel__slide'));
    const prevBtn = carousel.querySelector('.charts-carousel__nav--prev');
    const nextBtn = carousel.querySelector('.charts-carousel__nav--next');
    const dotsWrap = carousel.querySelector('.charts-carousel__dots');

    let index = 0;

    slides.forEach((_, i) => {
      const b = document.createElement('button');
      b.type = 'button'; b.setAttribute('role', 'tab');
      b.setAttribute('aria-controls', `chart-slide-${i}`);
      b.setAttribute('aria-selected', i === 0 ? 'true' : 'false');
      b.addEventListener('click', () => goTo(i));
      dotsWrap.appendChild(b);
    });
    slides.forEach((slide, i) => slide.id = `chart-slide-${i}`);

    function update() {
      slides = Array.from(carousel.querySelectorAll('.charts-carousel__slide'));
      track.style.transform = `translateX(-${index * 100}%)`;
      dotsWrap.querySelectorAll('button').forEach((b, i) => b.setAttribute('aria-selected', i === index ? 'true' : 'false'));
      setTimeout(() => {
        const ids = ['usersChart','jobsChart','applicationsChart','employersChart'];
        const targetId = ids[index];
        const target = targetId ? document.getElementById(targetId) : null;
        if (target) { try { Plotly.Plots.resize(target); } catch(e){} }
      }, 0);
      const show = slides.length > 1;
      [prevBtn, nextBtn, dotsWrap].forEach(el => { if (el) el.style.display = show ? '' : 'none'; });
    }
    function goTo(i) { index = Math.max(0, Math.min(slides.length - 1, i)); update(); }
    function next() { goTo(index + 1); }
    function prev() { goTo(index - 1); }
    if (nextBtn) nextBtn.addEventListener('click', next);
    if (prevBtn) prevBtn.addEventListener('click', prev);

    // Swipe support
    let startX = 0, dx = 0; const threshold = 40;
    track.addEventListener('touchstart', (e) => { startX = e.touches[0].clientX; dx = 0; }, { passive: true });
    track.addEventListener('touchmove', (e) => { dx = e.touches[0].clientX - startX; }, { passive: true });
    track.addEventListener('touchend', () => { if (dx > threshold) prev(); else if (dx < -threshold) next(); dx = 0; });
    carousel.addEventListener('keydown', (e) => { if (e.key === 'ArrowRight') next(); if (e.key === 'ArrowLeft') prev(); });

    // Autoplay with pause-on-hover and visibility
    let timer = null; const delay = 5000;
    function start() { if (timer || slides.length <= 1) return; timer = setInterval(() => goTo((index + 1) % slides.length), delay); }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }
    carousel.addEventListener('mouseenter', stop);
    carousel.addEventListener('mouseleave', start);
    carousel.addEventListener('touchstart', stop, { passive: true });
    carousel.addEventListener('touchend', start, { passive: true });
    document.addEventListener('visibilitychange', () => { document.hidden ? stop() : start(); });

    update();
    start();
  }

  // Modal confirmation for inline admin actions
  const modal = document.getElementById('confirmModal');
  const msgEl = document.getElementById('confirmModalMessage');
  const btnOk = document.getElementById('confirmOk');
  const btnCancel = document.getElementById('confirmCancel');
  const backdrop = document.querySelector('.rr-modal__backdrop');
  let pendingForm = null;

  function openModal(message, form) {
    pendingForm = form;
    if (msgEl) msgEl.textContent = message || 'Are you sure?';
    if (modal) { modal.classList.add('open'); modal.setAttribute('aria-hidden', 'false'); }
  }
  function closeModal() {
    if (modal) { modal.classList.remove('open'); modal.setAttribute('aria-hidden', 'true'); }
    pendingForm = null;
  }
  if (btnOk) btnOk.addEventListener('click', () => { if (pendingForm) pendingForm.submit(); closeModal(); });
  if (btnCancel) btnCancel.addEventListener('click', closeModal);
  if (backdrop) backdrop.addEventListener('click', closeModal);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

  document.querySelectorAll('form.js-confirm').forEach(form => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      openModal(form.dataset.message || 'Are you sure?', form);
    });
  });
});
