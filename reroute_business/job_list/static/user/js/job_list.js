function toggleFilters() {
  const sidebar = document.getElementById('filtersSidebar');
  const backdrop = document.getElementById('filtersBackdrop');
  const isOpen = sidebar.classList.contains('open');

  if (!isOpen) {
    sidebar.classList.add('open');
    sidebar.setAttribute('aria-hidden', 'false');
    if (backdrop) {
      backdrop.hidden = false;
      backdrop.classList.add('show');
    }
    document.body.classList.add('no-scroll');
  } else {
    sidebar.classList.remove('open');
    sidebar.setAttribute('aria-hidden', 'true');
    if (backdrop) {
      backdrop.classList.remove('show');
      // delay hiding until transition ends
      setTimeout(() => { backdrop.hidden = true; }, 200);
    }
    document.body.classList.remove('no-scroll');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('jobFilterForm');
  const results = document.getElementById('jobResults');
  const sidebar = document.getElementById('filtersSidebar');
  const backdrop = document.getElementById('filtersBackdrop');

  function collectFilters() {
    const params = new URLSearchParams();
    // Search bar fields
    if (form) {
      const q = form.querySelector('input[name="q"]');
      const zip = form.querySelector('input[name="zip"]');
      if (q && q.value.trim()) params.set('q', q.value.trim());
      if (zip && zip.value.trim()) params.set('zip', zip.value.trim());
    }
    // Sidebar filters
    if (sidebar) {
      // Job types (checkboxes, repeated)
      sidebar.querySelectorAll('input[name="type"]:checked').forEach(cb => {
        params.append('type', cb.value);
      });
      // Preset zip (radios)
      const rz = sidebar.querySelector('input[name="preset_zip"]:checked');
      if (rz && rz.value !== '') params.set('preset_zip', rz.value);
      // Radius select
      const radius = sidebar.querySelector('select[name="radius"]');
      if (radius && radius.value) params.set('radius', radius.value);
    }
    return params;
  }

  async function ajaxUpdate() {
    if (!results) return;
    const params = collectFilters();
    const url = `${window.location.pathname}?${params.toString()}`;
    try {
      const res = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      const html = await res.text();
      if (res.ok) {
        results.innerHTML = html;
        // No need to rebind save-job events due to delegation below
      }
    } catch (e) {
      console.error('Filter update failed', e);
    }
  }

  // Intercept form submit for search to use AJAX
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      ajaxUpdate();
    });
  }

  // Listen to all relevant filter changes (sidebar + search bar)
  const liveSelectors = [
    '#filtersSidebar input[type="checkbox"]',
    '#filtersSidebar input[type="radio"]',
    '#filtersSidebar select[name="radius"]',
    '#jobFilterForm input[name="q"]',
    '#jobFilterForm input[name="zip"]'
  ];
  document.querySelectorAll(liveSelectors.join(',')).forEach(el => {
    el.addEventListener('change', ajaxUpdate);
    if (el.tagName === 'INPUT' && el.name === 'q') {
      // Enter key on search should trigger AJAX, already handled by submit; add small debounce on typing
      let t;
      el.addEventListener('input', () => { clearTimeout(t); t = setTimeout(ajaxUpdate, 400); });
    }
  });

  // Backdrop and ESC to close drawer (mobile)
  if (backdrop) {
    backdrop.addEventListener('click', () => { if (sidebar && sidebar.classList.contains('open')) toggleFilters(); });
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && sidebar && sidebar.classList.contains('open')) {
      toggleFilters();
    }
  });

  // When resizing to desktop, ensure drawer state is reset
  let lastIsMobile = window.innerWidth <= 1023;
  window.addEventListener('resize', () => {
    const isMobile = window.innerWidth <= 1023;
    if (!isMobile && lastIsMobile) {
      // leaving mobile -> desktop
      if (sidebar) {
        sidebar.classList.remove('open');
        sidebar.removeAttribute('aria-hidden');
      }
      if (backdrop) {
        backdrop.classList.remove('show');
        backdrop.hidden = true;
      }
      document.body.classList.remove('no-scroll');
    }
    lastIsMobile = isMobile;
  });
});

document.addEventListener('DOMContentLoaded', () => {
  if (!toggleSaveUrl || !csrfToken) {
    console.error("Missing toggleSaveUrl or csrfToken.");
    return;
  }

  // Use event delegation on the container
  document.body.addEventListener('click', async (event) => {
    const button = event.target.closest('.save-job-btn');

    if (!button) return;

    event.preventDefault();
    event.stopPropagation();

    const jobId = button.dataset.jobId;
    const icon = button.querySelector('.bookmark-icon');
    const label = button.querySelector('.save-label');

    // Prevent double click spamming
    if (button.disabled) return;
    button.disabled = true;

    try {
      const response = await fetch(toggleSaveUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `job_id=${jobId}`
      });

      const data = await response.json();
      console.log("Save toggle response:", data);  // 👀 Debug

      if (data.status === 'saved') {
        button.classList.add('saved');
        icon.classList.add('filled');
        label.textContent = 'Saved';
      } else if (data.status === 'unsaved') {
        button.classList.remove('saved');
        icon.classList.remove('filled');
        label.textContent = 'Save Job';
      }
    } catch (error) {
      console.error('Toggle save error:', error);
    } finally {
      button.disabled = false;
    }
  });
});
