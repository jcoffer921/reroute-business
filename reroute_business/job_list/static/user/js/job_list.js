function toggleFilters(open) {
  const sidebar = document.getElementById('filtersSidebar');
  const backdrop = document.getElementById('filtersBackdrop');
  if (!sidebar) return;

  const shouldOpen = typeof open === 'boolean' ? open : !sidebar.classList.contains('open');
  sidebar.classList.toggle('open', shouldOpen);
  sidebar.setAttribute('aria-hidden', shouldOpen ? 'false' : 'true');

  if (backdrop) {
    if (shouldOpen) {
      backdrop.hidden = false;
      backdrop.classList.add('show');
    } else {
      backdrop.classList.remove('show');
      setTimeout(() => {
        backdrop.hidden = true;
      }, 180);
    }
  }
  document.body.classList.toggle('no-scroll', shouldOpen);
}

function deterministicMatchScore(jobId, rawTags) {
  const tags = (rawTags || '').split(',').map((tag) => tag.trim()).filter(Boolean);
  const base = Number(jobId || 0);
  const score = 55 + ((base * 11 + tags.length * 9) % 36);
  return Math.max(55, Math.min(92, score));
}

function hydrateJobCards(container) {
  const root = container || document;

  root.querySelectorAll('[data-job-tags]').forEach((holder) => {
    const tags = (holder.dataset.tags || '').split(',').map((tag) => tag.trim()).filter(Boolean);
    holder.innerHTML = '';
    if (!tags.length) {
      holder.innerHTML = '<span class="rr-tag">General</span>';
      return;
    }
    tags.forEach((tag) => {
      const chip = document.createElement('span');
      chip.className = 'rr-tag';
      chip.textContent = tag;
      holder.appendChild(chip);
    });
  });

  root.querySelectorAll('[data-job-score]').forEach((node) => {
    const score = deterministicMatchScore(node.dataset.jobId, node.dataset.tags);
    const fill = node.querySelector('[data-job-score-fill]');
    const label = node.querySelector('[data-job-score-label]');
    if (fill) fill.style.width = `${score}%`;
    if (label) label.textContent = `${score}%`;
  });

  root.querySelectorAll('.rr-accordion-toggle').forEach((btn) => {
    if (btn.dataset.bound === '1') return;
    btn.dataset.bound = '1';
    btn.addEventListener('click', () => {
      const panel = btn.closest('.rr-accordion')?.querySelector('.rr-accordion-panel');
      if (!panel) return;
      const expanded = btn.getAttribute('aria-expanded') === 'true';
      btn.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      panel.hidden = expanded;
    });
  });
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[1]) : '';
}

function initPhaseModal() {
  const modal = document.getElementById('jobsPhaseModal');
  if (!modal) return;

  const closeModal = () => {
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('no-scroll');
  };

  modal.querySelectorAll('[data-phase-close]').forEach((el) => {
    el.addEventListener('click', closeModal);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && modal.getAttribute('aria-hidden') === 'false') closeModal();
  });

  modal.setAttribute('aria-hidden', 'false');
  document.body.classList.add('no-scroll');
}

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('jobFilterForm');
  const results = document.getElementById('jobResults');
  const sidebar = document.getElementById('filtersSidebar');
  const backdrop = document.getElementById('filtersBackdrop');
  const openBtn = document.querySelector('.mobile-filter-toggle');
  const closeBtn = document.querySelector('.filters-close');

  hydrateJobCards(document);
  initPhaseModal();

  const collectFilters = () => {
    const params = new URLSearchParams();

    if (form) {
      const q = form.querySelector('input[name="q"]');
      const zip = form.querySelector('input[name="zip"]');
      const radius = form.querySelector('select[name="radius"]');
      if (q && q.value.trim()) params.set('q', q.value.trim());
      if (zip && zip.value.trim()) params.set('zip', zip.value.trim());
      if (radius && radius.value) params.set('radius', radius.value);
    }

    if (sidebar) {
      sidebar.querySelectorAll('input[name="type"]:checked').forEach((cb) => {
        params.append('type', cb.value);
      });
    }

    return params;
  };

  const ajaxUpdate = async () => {
    if (!results || !form) return;
    const params = collectFilters();
    const url = `${window.location.pathname}?${params.toString()}`;

    try {
      const res = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      const html = await res.text();
      if (!res.ok) return;
      results.innerHTML = html;
      hydrateJobCards(results);
    } catch (err) {
      console.error('Job board refresh failed', err);
    }
  };

  if (form) {
    form.addEventListener('submit', (event) => {
      if (!results) return;
      event.preventDefault();
      ajaxUpdate();
    });

    const keyword = form.querySelector('input[name="q"]');
    if (keyword) {
      let timer;
      keyword.addEventListener('input', () => {
        if (!results) return;
        clearTimeout(timer);
        timer = setTimeout(ajaxUpdate, 350);
      });
    }

    form.querySelectorAll('input[name="zip"], select[name="radius"]').forEach((el) => {
      el.addEventListener('change', () => {
        if (results) ajaxUpdate();
      });
    });
  }

  if (sidebar) {
    sidebar.querySelectorAll('input[name="type"]').forEach((el) => {
      el.addEventListener('change', () => {
        if (results) ajaxUpdate();
      });
    });
  }

  if (openBtn) openBtn.addEventListener('click', () => toggleFilters(true));
  if (closeBtn) closeBtn.addEventListener('click', () => toggleFilters(false));
  if (backdrop) backdrop.addEventListener('click', () => toggleFilters(false));

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && sidebar && sidebar.classList.contains('open')) {
      toggleFilters(false);
    }
  });

  const boot = document.getElementById('jobListBoot');
  const toggleSaveUrl = boot?.dataset.toggleSaveUrl || '';
  const csrfToken = getCookie('csrftoken');

  document.body.addEventListener('click', async (event) => {
    const button = event.target.closest('.save-job-btn');
    if (!button || !toggleSaveUrl || !csrfToken) return;

    event.preventDefault();

    const jobId = button.dataset.jobId;
    const icon = button.querySelector('.bookmark-icon');
    const label = button.querySelector('.save-label');

    if (button.disabled) return;
    button.disabled = true;

    try {
      const response = await fetch(toggleSaveUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `job_id=${jobId}`,
      });

      const data = await response.json();
      if (data.status === 'saved') {
        button.classList.add('saved');
        icon?.classList.add('filled');
        if (label) label.textContent = 'Saved';
      } else if (data.status === 'unsaved') {
        button.classList.remove('saved');
        icon?.classList.remove('filled');
        if (label) label.textContent = 'Save';
      }
    } catch (error) {
      console.error('Save toggle error', error);
    } finally {
      button.disabled = false;
    }
  });
});
