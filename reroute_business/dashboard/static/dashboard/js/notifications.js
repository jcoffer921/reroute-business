(function() {
  const tabs = document.querySelectorAll('.notifications-tabs .tab');
  const cards = Array.from(document.querySelectorAll('.notification-card'));
  const emptyState = document.getElementById('notificationsEmptyState');
  const markAllForm = document.getElementById('markAllForm');
  const unreadToggle = document.getElementById('unreadOnlyToggle');

  function getCSRFToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : (document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '');
  }

  async function ajaxMarkRead(id) {
    try {
      const res = await fetch(window.location.href, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCSRFToken(),
        },
        body: new URLSearchParams({ action: 'mark_read', id: String(id) }).toString(),
      });
      const data = await res.json().catch(() => ({}));
      return res.ok && data && data.ok;
    } catch (err) {
      return false;
    }
  }

  function updateCardUIAsRead(card) {
    card.classList.remove('unread');
    const form = card.querySelector('.mark-read-form');
    if (form) form.remove();
    syncNavbarUnreadBadge();
  }

  function updateEmptyState(filter) {
    const visible = cards.filter(c => !c.hasAttribute('hidden'));
    if (visible.length > 0) {
      emptyState?.setAttribute('hidden','');
      return;
    }
    if (!emptyState) return;
    const map = {
      all: "You're all caught up.",
      jobs: 'No job notifications yet.',
      applications: 'No application updates yet.',
      invites: 'No invites yet.',
      platform: 'No platform updates yet.',
    };
    emptyState.querySelector('.empty-text').textContent = map[filter] || map.all;
    emptyState.removeAttribute('hidden');
  }

  function applyFilters() {
    const active = document.querySelector('.notifications-tabs .tab.active');
    const filter = active ? active.getAttribute('data-filter') : 'all';
    const unreadOnly = unreadToggle?.checked;
    cards.forEach(c => {
      const matchesType = filter === 'all' || c.getAttribute('data-type') === filter;
      const matchesUnread = !unreadOnly || c.classList.contains('unread');
      if (matchesType && matchesUnread) c.removeAttribute('hidden');
      else c.setAttribute('hidden','');
    });
    updateEmptyState(filter);
  }

  tabs.forEach(tab => tab.addEventListener('click', () => {
    tabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    applyFilters();
  }));

  unreadToggle?.addEventListener('change', applyFilters);

  if (markAllForm) {
    markAllForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const formData = new FormData(markAllForm);
      try {
        const res = await fetch(window.location.href, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
          },
          credentials: 'same-origin',
          body: new URLSearchParams(formData).toString(),
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data && data.ok) {
          cards.forEach(card => {
            if (card.classList.contains('unread')) {
              card.classList.remove('unread');
              const form = card.querySelector('.mark-read-form');
              if (form) form.remove();
            }
          });
          updateNavbarBadge(0);
          applyFilters();
        }
      } catch(_) {}
    });
  }

  // Card click marks as read (and navigates if there is a URL)
  cards.forEach(card => {
    card.addEventListener('click', async (e) => {
      const target = e.target;
      if (target.closest('.mark-read-form')) return;
      const url = card.getAttribute('data-url');
      const markable = card.getAttribute('data-markable') === '1';
      const isUnread = card.classList.contains('unread');
      if (markable && isUnread) {
        const id = card.getAttribute('data-id');
        if (id) {
          const ok = await ajaxMarkRead(id);
          if (ok) updateCardUIAsRead(card);
        }
      }
      if (url && !target.closest('.btn-action')) {
        window.location.href = url;
      }
    });
  });

  // CTA click should also mark as read before navigating
  document.querySelectorAll('[data-cta]').forEach(link => {
    link.addEventListener('click', async (e) => {
      const card = link.closest('.notification-card');
      if (!card) return;
      if (!card.classList.contains('unread')) return;
      if (card.getAttribute('data-markable') !== '1') return;
      const id = card.getAttribute('data-id');
      if (!id) return;
      e.preventDefault();
      const ok = await ajaxMarkRead(id);
      if (ok) updateCardUIAsRead(card);
      window.location.href = link.getAttribute('href');
    });
  });

  // Intercept per-item mark-as-read forms
  document.querySelectorAll('.mark-read-form').forEach(form => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const id = form.getAttribute('data-id') || form.querySelector('input[name="id"]').value;
      const card = form.closest('.notification-card');
      const ok = await ajaxMarkRead(id);
      if (ok && card) updateCardUIAsRead(card);
      applyFilters();
    });
  });

  applyFilters();

  // Navbar badge helpers
  function computeUnreadCount() {
    return cards.filter(c => c.classList.contains('unread') && c.getAttribute('data-markable') === '1').length;
  }

  function updateNavbarBadge(count) {
    const anchors = document.querySelectorAll('a[href*="/dashboard/notifications"]');
    anchors.forEach(a => {
      let badge = a.querySelector('.nav-badge');
      if (count > 0) {
        if (!badge) {
          badge = document.createElement('span');
          badge.className = 'nav-badge';
          a.appendChild(badge);
        }
        badge.textContent = String(count);
      } else if (badge) {
        badge.remove();
      }
    });
  }

  function syncNavbarUnreadBadge() {
    updateNavbarBadge(computeUnreadCount());
  }
})();
