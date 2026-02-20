/* ==========================================================
    Accessible Blog Slider
    - Arrows, dots, keyboard, swipe
    - Resizes cleanly
    - Fully commented for readability
    ========================================================== */
(function () {
  // 1) Get DOM references
  const wrapper = document.getElementById('slidesWrapper');
  if (!wrapper) return; // Safety check if markup changes

  const slides = Array.from(wrapper.querySelectorAll('.slide'));
  const dotsContainer = document.getElementById('sliderDots');
  const prevBtn = document.querySelector('.slider-btn.prev');
  const nextBtn = document.querySelector('.slider-btn.next');

  // Early exit if no slides available
  if (!slides.length) return;

  // 2) Internal state
  let index = 0;          // current slide
  let isAnimating = false;

  // 3) Set dynamic widths so each slide fills the viewport
  function setSizes() {
    // Using CSS flex + scroll snapping; no inline styles needed.
    goTo(index, false);
  }

  // 4) Build clickable dots
  function buildDots() {
    dotsContainer.innerHTML = '';
    slides.forEach((_, i) => {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.className = 'dot';
      dot.setAttribute('aria-label', `Go to slide ${i + 1}`);
      dot.addEventListener('click', () => goTo(i));
      dotsContainer.appendChild(dot);
    });
    updateDots();
  }

  // 5) Update active dot styling + aria
  function updateDots() {
    const dots = Array.from(dotsContainer.children);
    dots.forEach((d, i) => {
      d.classList.toggle('active', i === index);
      d.setAttribute('aria-current', i === index ? 'true' : 'false');
    });
  }

  // 6) Move to specific slide (with optional animation)
  function goTo(i, animate = true) {
    if (isAnimating) return;
    index = Math.max(0, Math.min(i, slides.length - 1));
    isAnimating = true;
    const left = index * wrapper.clientWidth;
    try { wrapper.scrollTo({ left, behavior: animate ? 'smooth' : 'auto' }); } catch(_) { wrapper.scrollLeft = left; }
    setTimeout(() => { isAnimating = false; }, animate ? 350 : 0);
    updateDots();
  }

  // 7) Convenience next/prev
  function next() { goTo((index + 1) % slides.length); }
  function prev() { goTo((index - 1 + slides.length) % slides.length); }

  // 8) Wire up buttons
  if (prevBtn) prevBtn.addEventListener('click', prev);
  if (nextBtn) nextBtn.addEventListener('click', next);

  // 9) Keyboard navigation (make wrapper focusable)
  wrapper.setAttribute('tabindex', '0');
  wrapper.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight') next();
    if (e.key === 'ArrowLeft') prev();
  });

  // 10) Touch / swipe support
  let startX = 0, deltaX = 0;
  wrapper.addEventListener('touchstart', (e) => {
    startX = e.touches[0].clientX;
    deltaX = 0;
  }, { passive: true });

  wrapper.addEventListener('touchmove', (e) => {
    deltaX = e.touches[0].clientX - startX;
  }, { passive: true });

  wrapper.addEventListener('touchend', () => {
    // Simple threshold for swipe
    if (Math.abs(deltaX) > 50) (deltaX < 0 ? next : prev)();
  });

  // 11) Handle window resizes to keep widths correct
  window.addEventListener('resize', setSizes);

  // 12) Initialize
  setSizes();
  buildDots();

  // 13) Optional autoplay (commented out for accessibility)
  // let timer = setInterval(next, 6000);
  // wrapper.addEventListener('mouseenter', () => clearInterval(timer));
  // wrapper.addEventListener('mouseleave', () => timer = setInterval(next, 6000));
})();

// Lightweight reveal-on-scroll for testimonial pull-quote
(function () {
  const items = document.querySelectorAll('.testimonial-section .reveal-up');
  if (!items.length || !('IntersectionObserver' in window)) return;

  const obs = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.2 });

  items.forEach((el, i) => {
    const d = Math.min(10, Math.max(0, Math.round(i)));
    el.classList.add(`delay-${d}`);
    obs.observe(el);
  });
})();

// Calm reveal-on-scroll for homepage sections and grouped items
(function () {
  const revealItems = document.querySelectorAll('.reveal, .reveal-item');
  if (!revealItems.length) return;

  document.documentElement.classList.add('reveal-enabled');

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const showAll = () => revealItems.forEach(el => el.classList.add('is-visible'));
  if (reducedMotion.matches || !('IntersectionObserver' in window)) {
    showAll();
    return;
  }

  document.querySelectorAll('.reveal-group').forEach(group => {
    const items = group.querySelectorAll('.reveal-item');
    items.forEach((item, index) => {
      const delay = Math.min(index, 6) * 80;
      item.style.setProperty('--reveal-delay', `${delay}ms`);
    });
  });

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.2, rootMargin: '0px 0px -10% 0px' });

  revealItems.forEach(el => observer.observe(el));
})();

// Track homepage "Ongoing Support" card engagement
(function () {
  const cards = document.querySelectorAll('.support-card[data-card-name]');
  if (!cards.length) return;

  const supportGrid = document.querySelector('.support-grid[data-user-logged-in]');
  const isLoggedIn = supportGrid && supportGrid.getAttribute('data-user-logged-in') === 'true';

  cards.forEach((card) => {
    card.addEventListener('click', () => {
      const payload = {
        event: 'homepage_card_click',
        card_name: card.getAttribute('data-card-name') || '',
        user_logged_in: !!isLoggedIn,
        timestamp: new Date().toISOString(),
      };

      if (Array.isArray(window.dataLayer)) {
        window.dataLayer.push(payload);
      }

      if (typeof window.gtag === 'function') {
        window.gtag('event', 'homepage_card_click', {
          card_name: payload.card_name,
          user_logged_in: payload.user_logged_in,
          timestamp: payload.timestamp,
        });
      }

      window.dispatchEvent(new CustomEvent('homepage_card_click', { detail: payload }));
    });
  });
})();
