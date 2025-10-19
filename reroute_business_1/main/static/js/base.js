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
    backdrop.style.position = 'fixed';
    backdrop.style.inset = '0';
    backdrop.style.background = 'rgba(0,0,0,.4)';
    backdrop.style.zIndex = '1999';
    backdrop.style.display = 'none';
    document.body.appendChild(backdrop);
  }

  // Focus trap utils (keeps keyboard focus inside the drawer while open)
  function getFocusable(root) {
    return Array.from(root.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )).filter(el => el.offsetParent !== null || el === root);
  }

  let lastFocusedBeforeOpen = null;

  function openMobileMenu() {
    if (!mobileMenu) return;

    // Remember focus to restore on close
    lastFocusedBeforeOpen = document.activeElement;

    // Show drawer
    mobileMenu.classList.add('show');            // your CSS uses .mobile-menu.show { left: 0; }
    mobileMenu.setAttribute('aria-hidden', 'false');
    document.body.classList.add('no-scroll');    // prevent background scroll
    hamburgerBtn?.setAttribute('aria-expanded', 'true');

    // Show backdrop
    if (backdrop) {
      backdrop.style.display = 'block';
      backdrop.removeAttribute('hidden');
    }

    // Move focus inside drawer (first focusable, otherwise drawer itself)
    const first = getFocusable(mobileMenu)[0] || mobileMenu;
    first.focus({ preventScroll: true });
  }

  function closeMobileMenu() {
    if (!mobileMenu) return;

    mobileMenu.classList.remove('show');
    mobileMenu.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('no-scroll');
    hamburgerBtn?.setAttribute('aria-expanded', 'false');

    if (backdrop) {
      backdrop.style.display = 'none';
      backdrop.setAttribute('hidden', '');
    }

    // Restore focus to whatever had it before open
    if (lastFocusedBeforeOpen && document.contains(lastFocusedBeforeOpen)) {
      lastFocusedBeforeOpen.focus({ preventScroll: true });
    } else {
      hamburgerBtn?.focus({ preventScroll: true });
    }
  }

  // Keep your inline HTML working too if you still call toggleMobileMenu()
  window.toggleMobileMenu = function toggleMobileMenu() {
    if (!mobileMenu) return;
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
})();
