// Guard all DOM access so no TypeErrors occur if elements are missing.
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupDashboard);
} else {
  setupDashboard();
}

function setupDashboard() {
  initTips();
  initTabs();
  initInterviewsModal();
  initProgressTiles();
  initSliders();
}

// Tip rotation with null checks (avoids addEventListener on null)
function initTips() {
  const tipElement = document.getElementById('tipText');
  const nextTipBtn = document.getElementById('nextTipBtn');
  if (!tipElement) return;

  const tips = [
    { text: 'Upload your resume to unlock job matches instantly.', type: 'profile' },
    { text: 'Add a profile picture to build trust with employers.', type: 'profile' },
    { text: 'Keep your skills list current for better matching.', type: 'profile' },
    { text: 'Set location preferences to see nearby roles and orgs.', type: 'job_search' },
    { text: 'Check ReRoute daily — new jobs and orgs get added often.', type: 'job_search' },
    { text: 'Follow up on applications a few days after applying.', type: 'job_search' },
    { text: 'Save jobs you like so we can prioritize similar matches.', type: 'job_search' },
    { text: 'Finish one learning module a week to keep momentum.', type: 'modules' },
    { text: 'Bookmark organizations that can help with housing or legal support.', type: 'orgs' },
    { text: 'Small, steady actions stack up — you are making progress.', type: 'motivation' },
    { text: 'Your story matters. Lead with your strengths and growth.', type: 'motivation' },
  ];

  let index = Math.floor(Math.random() * tips.length);

  const showTip = () => {
    tipElement.style.opacity = '0';
    setTimeout(() => {
      tipElement.textContent = tips[index].text;
      tipElement.style.opacity = '1';
      index = (index + 1) % tips.length;
    }, 200);
  };

  showTip();
  const interval = setInterval(showTip, 8000);

  if (nextTipBtn) {
    nextTipBtn.addEventListener('click', () => {
      clearInterval(interval);
      showTip();
    });
  }
}

// Tabs: safe even if group has no tabs/panels
function initTabs() {
  const groups = document.querySelectorAll('[data-tab-group]');
  groups.forEach(group => {
    const tabs = group.querySelectorAll('.tab-btn');
    const panels = group.querySelectorAll('.tab-panel');
    if (!tabs.length || !panels.length) return;

    const activate = (name) => {
      tabs.forEach(tab => tab.classList.toggle('active', tab.dataset.tab === name));
      panels.forEach(panel => panel.classList.toggle('active', panel.dataset.tabPanel === name));
    };

    tabs.forEach(tab => {
      tab.addEventListener('click', () => activate(tab.dataset.tab));
    });

    const defaultTab = group.querySelector('.tab-btn.active')?.dataset.tab || tabs[0].dataset.tab;
    activate(defaultTab);
  });
}

// Interviews modal: all operations guarded so it no-ops if any piece is absent
function initInterviewsModal() {
  const openBtn = document.getElementById('openUserInterviews');
  const backdrop = document.getElementById('userInterviewsBackdrop');
  const modal = document.getElementById('userInterviewsModal');
  const content = document.getElementById('userInterviewsContent');

  if (!openBtn || !backdrop || !modal || !content) return;

  const close = () => {
    backdrop.classList.add('hidden');
    modal.classList.add('hidden');
  };

  const showToast = (msg) => {
    const t = document.createElement('div');
    t.className = 'toast toast-success';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.classList.add('show'), 10);
    setTimeout(() => {
      t.classList.remove('show');
      t.addEventListener('transitionend', () => t.remove(), { once: true });
    }, 2000);
  };

  const bindModalEvents = () => {
    content.querySelectorAll('[data-close-user-interviews]').forEach(btn => btn.addEventListener('click', close));
    backdrop.addEventListener('click', close);

    content.querySelectorAll('.accept-form').forEach(form => {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const res = await fetch(form.action, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' }, body: new FormData(form) });
        if (res.ok) {
          form.closest('.interview-item')?.querySelectorAll('button, input, summary').forEach(el => { el.disabled = true; });
          showToast('Interview accepted');
        }
      });
    });

    content.querySelectorAll('.resched-form').forEach(form => {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const res = await fetch(form.action, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' }, body: new FormData(form) });
        if (res.ok) {
          form.closest('.interview-item')?.querySelectorAll('button, input, summary').forEach(el => { el.disabled = true; });
          showToast('Reschedule request sent');
        }
      });
    });
  };

  const open = () => {
    fetch('/dashboard/user/interviews/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(r => r.text())
      .then(html => {
        content.innerHTML = html;
        backdrop.classList.remove('hidden');
        modal.classList.remove('hidden');
        bindModalEvents();
      })
      .catch(() => {
        content.innerHTML = '<div style="padding:12px;">Failed to load interviews.</div>';
        backdrop.classList.remove('hidden');
        modal.classList.remove('hidden');
      });
  };

  openBtn.addEventListener('click', open);
}

// Progress rings: set CSS variable only when tile exists
function initProgressTiles() {
  document.querySelectorAll('.progress-tile').forEach(tile => {
    const value = parseFloat(tile.dataset.value || '0');
    if (!Number.isFinite(value)) {
      tile.style.setProperty('--value', 0);
      return;
    }
    tile.style.setProperty('--value', value);
  });
}

// Generic sliders (for future carousels) with null guards on scrollLeft
function initSliders() {
  const sliders = document.querySelectorAll('[data-slider]');
  sliders.forEach(slider => {
    const container = slider.querySelector('[data-slider-track]');
    const prev = slider.querySelector('[data-slider-prev]');
    const next = slider.querySelector('[data-slider-next]');
    if (!container) return; // nothing to wire

    const SCROLL_AMOUNT = parseInt(slider.dataset.sliderStep || '320', 10);

    const updateButtons = () => {
      if (!prev || !next) return;
      const maxScroll = container.scrollWidth - container.clientWidth;
      prev.disabled = container.scrollLeft <= 0;
      next.disabled = container.scrollLeft >= maxScroll;
    };

    if (prev) {
      prev.addEventListener('click', () => {
        container.scrollBy({ left: -SCROLL_AMOUNT, behavior: 'smooth' });
        setTimeout(updateButtons, 300);
      });
    }

    if (next) {
      next.addEventListener('click', () => {
        container.scrollBy({ left: SCROLL_AMOUNT, behavior: 'smooth' });
        setTimeout(updateButtons, 300);
      });
    }

    container.addEventListener('scroll', updateButtons, { passive: true });
    updateButtons();
  });
}
