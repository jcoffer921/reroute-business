/* =============================================================================
 * ReRoute Base JS
 * - Mobile drawer (hamburger) using #mobileMenu + .show
 * - Optional backdrop #mobileBackdrop (auto-created if missing)
 * - Right-side profile dropdown (desktop)
 * - Accessibility: ARIA updates, focus management, Esc to close, click-outside
 * ============================================================================= */

(() => {
  const DESKTOP_MIN = 769; // keep aligned with your CSS breakpoint

  // Mini helpers
  const qs  = (sel, root = document) => root.querySelector(sel);
  const on  = (el, ev, fn, opts) => el && el.addEventListener(ev, fn, opts);

  /* -------------------------- MOBILE DRAWER -------------------------- */
  const mobileMenu   = qs('#mobileMenu');        // <div id="mobileMenu" class="mobile-menu">
  const hamburgerBtn = qs('.hamburger');         // <button class="hamburger">☰</button>
  let   backdrop     = qs('#mobileBackdrop');    // optional — we’ll create one if it’s missing

  // Create a backdrop if not present (non-invasive)
  if (!backdrop && mobileMenu) {
    backdrop = document.createElement('div');
    backdrop.id = 'mobileBackdrop';
    backdrop.className = 'mobile-backdrop';
    backdrop.setAttribute('hidden', '');
    document.body.appendChild(backdrop);
  }

  // Focus trap utils (keeps keyboard focus inside the drawer while open)
  function getFocusable(root) {
    return Array.from(root.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )).filter(el => el.offsetParent !== null || el === root);
  }

  let lastFocusedBeforeOpen = null;
  let savedScrollY = 0;

  function lockBodyScroll() {
    savedScrollY = window.scrollY || 0;
    document.body.classList.add('no-scroll');
    document.body.style.position = 'fixed';
    document.body.style.top = `-${savedScrollY}px`;
    document.body.style.left = '0';
    document.body.style.right = '0';
    document.body.style.width = '100%';
  }

  function unlockBodyScroll() {
    document.body.classList.remove('no-scroll');
    document.body.style.position = '';
    document.body.style.top = '';
    document.body.style.left = '';
    document.body.style.right = '';
    document.body.style.width = '';
    window.scrollTo(0, savedScrollY);
  }

  function openMobileMenu() {
    if (!mobileMenu) return;

    // Remember focus to restore on close
    lastFocusedBeforeOpen = document.activeElement;

    // Show drawer
    mobileMenu.classList.add('show');            // your CSS uses .mobile-menu.show { left: 0; }
    mobileMenu.setAttribute('aria-hidden', 'false');
    lockBodyScroll();
    hamburgerBtn?.setAttribute('aria-expanded', 'true');
    hamburgerBtn?.setAttribute('aria-label', 'Close menu');

    // Show backdrop
    if (backdrop) { backdrop.classList.add('show'); backdrop.removeAttribute('hidden'); }

    // Move focus inside drawer (first focusable, otherwise drawer itself)
    const first = getFocusable(mobileMenu)[0] || mobileMenu;
    first.focus({ preventScroll: true });
  }

  function closeMobileMenu() {
    if (!mobileMenu) return;

    mobileMenu.classList.remove('show');
    mobileMenu.setAttribute('aria-hidden', 'true');
    unlockBodyScroll();
    hamburgerBtn?.setAttribute('aria-expanded', 'false');
    hamburgerBtn?.setAttribute('aria-label', 'Open menu');

    if (backdrop) { backdrop.classList.remove('show'); backdrop.setAttribute('hidden', ''); }

    // Restore focus to whatever had it before open
    if (lastFocusedBeforeOpen && document.contains(lastFocusedBeforeOpen)) {
      lastFocusedBeforeOpen.focus({ preventScroll: true });
    } else {
      hamburgerBtn?.focus({ preventScroll: true });
    }
  }

  // Keep your inline HTML working too if you still call toggleMobileMenu()
  window.closeMobileMenu = closeMobileMenu;
  window.toggleMobileMenu = function toggleMobileMenu(forceOpen) {
    if (!mobileMenu) return;
    if (typeof forceOpen === 'boolean') {
      if (forceOpen) openMobileMenu();
      else closeMobileMenu();
      return;
    }
    mobileMenu.classList.contains('show') ? closeMobileMenu() : openMobileMenu();
  };

  if (mobileMenu) {
    // Open via hamburger
    on(hamburgerBtn, 'click', (e) => { e.preventDefault(); openMobileMenu(); }, { passive: true });

    // Close via dedicated close button inside the drawer
    const closeBtn = mobileMenu.querySelector('[data-close-mobile]');
    on(closeBtn, 'click', (e) => { e.preventDefault(); closeMobileMenu(); }, { passive: true });

    // Close when clicking any link/button inside the drawer
    on(mobileMenu, 'click', (e) => {
      if (e.target.closest('a') || e.target.closest('button[type="submit"]') || e.target.closest('.logout-btn')) {
        closeMobileMenu();
      }
    });

    // Close by clicking backdrop
    on(backdrop, 'click', () => closeMobileMenu(), { passive: true });

    // Focus trap while open
    on(mobileMenu, 'keydown', (e) => {
      if (e.key !== 'Tab' || !mobileMenu.classList.contains('show')) return;
      const f = getFocusable(mobileMenu);
      if (!f.length) return;
      const first = f[0];
      const last  = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        last.focus(); e.preventDefault();
      } else if (!e.shiftKey && document.activeElement === last) {
        first.focus(); e.preventDefault();
      }
    });

    // Close on Escape
    on(document, 'keydown', (e) => {
      if (e.key === 'Escape' && mobileMenu.classList.contains('show')) closeMobileMenu();
    });

    // Auto-close if resized to desktop
    let resizeTimer;
    on(window, 'resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (window.innerWidth >= DESKTOP_MIN && mobileMenu.classList.contains('show')) {
          closeMobileMenu();
        }
      }, 120);
    });
  }

  /* -------------------- RIGHT-SIDE PROFILE DROPDOWN ------------------- */
  // Desktop-only dropdown (CSS hides .user-profile-right on mobile)
  const profileBtn   = qs('#userMenuButton');   // initials button
  const profilePanel = qs('#userDropdown');     // dropdown panel
  const arrowIcon    = qs('#arrow-icon');       // ▼ / ▲

  function openProfile() {
    if (!profilePanel || !profileBtn) return;
    profilePanel.classList.add('show');         // CSS: .user-dropdown.show { display:block; }
    profileBtn.setAttribute('aria-expanded', 'true');
    if (arrowIcon) arrowIcon.textContent = '▲';
  }
  function closeProfile() {
    if (!profilePanel || !profileBtn) return;
    profilePanel.classList.remove('show');
    profileBtn.setAttribute('aria-expanded', 'false');
    if (arrowIcon) arrowIcon.textContent = '▼';
  }
  function toggleProfile() {
    if (!profilePanel) return;
    profilePanel.classList.contains('show') ? closeProfile() : openProfile();
  }

  if (profileBtn && profilePanel) {
    on(profileBtn, 'click', (e) => { e.stopPropagation(); toggleProfile(); }, { passive: true });
    on(profileBtn, 'keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleProfile(); }
    });
    on(document, 'click', (e) => {
      if (!profilePanel.contains(e.target) && !profileBtn.contains(e.target)) closeProfile();
    });
    on(document, 'keydown', (e) => { if (e.key === 'Escape') closeProfile(); });
    on(profilePanel, 'click', (e) => {
      if (e.target.closest('a') || e.target.closest('button')) closeProfile();
    });
    on(window, 'resize', () => { if (window.innerWidth < DESKTOP_MIN) closeProfile(); });
  }

  /* ------------------------ NAV AUTO-HIDE ------------------------- */
  const navbar = qs('[data-navbar]');
  if (navbar) {
    const HIDE_THRESHOLD = 12;
    const SHADOW_THRESHOLD = 8;
    const AUTOHIDE_MIN_WIDTH = 768;
    let lastScrollY = window.scrollY || 0;
    let ticking = false;

    const setState = (currentY) => {
      const isNearTop = currentY <= HIDE_THRESHOLD;
      const isScrollingDown = currentY > lastScrollY;
      const allowAutohide = window.innerWidth >= AUTOHIDE_MIN_WIDTH;

      navbar.classList.toggle('navbar--shadow', currentY > SHADOW_THRESHOLD);

      if (!allowAutohide) {
        navbar.classList.remove('navbar--hidden');
        lastScrollY = currentY;
        return;
      }

      if (isNearTop) {
        navbar.classList.remove('navbar--hidden');
      } else if (isScrollingDown) {
        navbar.classList.add('navbar--hidden');
      } else {
        navbar.classList.remove('navbar--hidden');
      }

      lastScrollY = currentY;
    };

    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(() => {
        setState(window.scrollY || 0);
        ticking = false;
      });
    };

    setState(lastScrollY);
    on(window, 'scroll', onScroll, { passive: true });
    on(window, 'resize', () => setState(window.scrollY || 0), { passive: true });
  }

  /* -------------------------- CSP helpers --------------------------- */
  // Prevent default navigation for menu items purely used to open dropdowns
  document.querySelectorAll('.nav-item.has-dropdown > a.no-nav').forEach(a => {
    a.addEventListener('click', (e) => { e.preventDefault(); });
  });
  // Close flash alerts without inline handlers
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-close-alert]');
    if (btn) {
      const alert = btn.closest('.alert');
      if (alert) alert.remove();
    }
  });
})();
