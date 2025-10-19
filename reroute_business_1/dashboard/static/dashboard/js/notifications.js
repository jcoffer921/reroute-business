// Notifications page interactions: tabs filter, empty states, and drawer
(function() {
  const tabs = document.querySelectorAll('.notifications-tabs .tab');
  const cards = Array.from(document.querySelectorAll('.notification-card'));
  const emptyState = document.getElementById('notificationsEmptyState');
  const markAllForm = document.getElementById('markAllForm');

  const drawer = document.getElementById('notifDrawer');
  const overlay = document.getElementById('notifDrawerOverlay');
  const drawerTitle = document.getElementById('notifDrawerTitle');
  const drawerMsg = document.getElementById('notifDrawerMessage');
  const drawerTime = document.getElementById('notifDrawerTime');
  const drawerLink = document.getElementById('notifDrawerLink');
  const closeBtns = [document.getElementById('notifDrawerClose'), document.getElementById('notifDrawerClose2')].filter(Boolean);
  const MARK_ON_OPEN = true; // toggle to false to disable auto mark as read on open

  function getCSRFToken() {
    // Prefer cookie (Django default name 'csrftoken')
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
    const dot = card.querySelector('.meta .unread-dot');
    if (dot) dot.remove();
    const form = card.querySelector('.mark-read-form');
    if (form) form.remove();
    // After updating the card, sync the navbar badge
    syncNavbarUnreadBadge();
  }

  function updateEmptyState(filter) {
    // Count visible cards after filter applied
    const visible = cards.filter(c => c.style.display !== 'none');
    if (visible.length > 0) {
      if (emptyState) emptyState.style.display = 'none';
      return;
    }
    if (!emptyState) return;

    // Friendly message per tab
    const map = {
      all: "You're all caught up.",
      jobs: 'No job notifications yet — check back soon!',
      system: 'No system notifications yet.',
      admin: 'No admin announcements right now.',
      tips: 'No tips to show yet.'
    };
    emptyState.querySelector('.empty-text').textContent = map[filter] || map.all;
    emptyState.style.display = '';
  }

  function setActive(tab) {
    tabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    const filter = tab.getAttribute('data-filter');
    cards.forEach(c => {
      if (filter === 'all') {
        c.style.display = '';
      } else {
        c.style.display = (c.getAttribute('data-type') === filter) ? '' : 'none';
      }
    });
    updateEmptyState(filter);
  }

  tabs.forEach(tab => tab.addEventListener('click', () => setActive(tab)));

  // Lightweight toast
  function showToast(msg) {
    const toast = document.createElement('div');
    toast.className = 'toast toast-success';
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => { toast.classList.add('show'); }, 10);
    setTimeout(() => {
      toast.classList.remove('show');
      toast.addEventListener('transitionend', () => toast.remove(), { once: true });
    }, 2000);
  }

  // AJAX Mark All as Read
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
          // Update all cards locally
          cards.forEach(card => {
            if (card.classList.contains('unread')) {
              card.classList.remove('unread');
              const dot = card.querySelector('.meta .unread-dot');
              if (dot) dot.remove();
              const form = card.querySelector('.mark-read-form');
              if (form) form.remove();
            }
          });
          showToast('All notifications marked as read');
          // Navbar badge → zero
          updateNavbarBadge(0);
        }
      } catch(_) {}
    });
  }

  // Drawer helpers
  function openDrawer(fromCard) {
    if (!drawer || !overlay) return;
    drawerTitle.textContent = fromCard.getAttribute('data-title') || 'Notification';
    drawerMsg.textContent = fromCard.getAttribute('data-message') || '';
    drawerTime.textContent = fromCard.getAttribute('data-time') || '';
    const url = fromCard.getAttribute('data-url');
    if (url) {
      drawerLink.style.display = '';
      drawerLink.setAttribute('href', url);
    } else {
      drawerLink.style.display = 'none';
    }
    overlay.style.display = 'block';
    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');

    // Optional: mark-as-read when opening the drawer
    if (MARK_ON_OPEN && fromCard.getAttribute('data-markable') === '1' && fromCard.classList.contains('unread')) {
      const id = fromCard.getAttribute('data-id');
      if (id) {
        ajaxMarkRead(id).then((ok) => { if (ok) updateCardUIAsRead(fromCard); });
      }
    }
  }
  function closeDrawer() {
    if (!drawer || !overlay) return;
    drawer.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');
    overlay.style.display = 'none';
  }
  closeBtns.forEach(btn => btn && btn.addEventListener('click', closeDrawer));
  if (overlay) overlay.addEventListener('click', closeDrawer);

  // Click to open drawer, but ignore clicks on actionable elements
  cards.forEach(card => {
    card.addEventListener('click', (e) => {
      const target = e.target;
      // Ignore clicks on links, buttons, inputs, forms inside actions
      if (target.closest('a, button, input, form, .actions')) return;
      openDrawer(card);
    });
  });

  // Intercept per-item mark-as-read forms and do AJAX
  document.querySelectorAll('.mark-read-form').forEach(form => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const id = form.getAttribute('data-id') || form.querySelector('input[name="id"]').value;
      const card = form.closest('.notification-card');
      const ok = await ajaxMarkRead(id);
      if (ok && card) updateCardUIAsRead(card);
    });
  });

  // Initialize empty state visibility for default tab
  const active = document.querySelector('.notifications-tabs .tab.active');
  if (active) updateEmptyState(active.getAttribute('data-filter') || 'all');

  // ---------- Navbar badge helpers ----------
  function computeUnreadCount() {
    // Count only user-owned unread cards (data-markable="1")
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
        badge.style.display = '';
      } else if (badge) {
        badge.remove();
      }
    });
  }

  function syncNavbarUnreadBadge() {
    updateNavbarBadge(computeUnreadCount());
  }
})();
