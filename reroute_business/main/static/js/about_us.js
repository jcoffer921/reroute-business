/**
 * Mission section scroll polish
 * - Parallax-y lift + gentle overlay fade
 * - Mobile-friendly (IO + rAF), reduced-motion aware
 */
(function () {
  // ------- DOM targets -------
  const section = document.querySelector('.about-mission');
  if (!section) return;  // page guard

  const overlay = section.querySelector('.mission-overlay');
  const content = section.querySelector('.mission-content');
  const quote   = section.querySelector('.mission-quote');

  // ------- A11y: respect reduced motion -------
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) {
    // Keep everything static and reveal quote immediately
    if (overlay) overlay.style.background = 'rgba(255,255,255,0.35)';
    if (content) { content.style.transform = 'none'; content.style.opacity = '1'; }
    if (quote) requestAnimationFrame(() => quote.classList.add('visible'));
    return;
  }

  // ------- rAF loop control -------
  let ticking = false;
  let active  = false;

  function clamp(n, min, max) { return Math.max(min, Math.min(max, n)); }

  function updateFrame() {
    ticking = false;
    if (!active || !section || !content || !overlay) return;

    // Use viewport relative metrics to avoid layout thrash
    const rect = section.getBoundingClientRect();
    const h    = rect.height || 1;

    // Visible if intersects viewport at all
    const inView = rect.bottom > 0 && rect.top < window.innerHeight;
    if (!inView) return;

    // Compute progress: 0 when top is at element top, ~1 as we move through its height
    // Derived from original formula: progress = 1 - rect.top / height
    const rawProgress = 1 - (rect.top / h);
    const progress    = clamp(rawProgress, 0, 1);  // 0..1

    // Apply subtle effects
    const alpha   = clamp(progress, 0, 0.95);     // overlay fade up to 0.95
    const liftPx  = -(progress * 20);             // translate up to -20px
    const opacity = 1 - (progress * 0.30);        // fade to 70%

    overlay.style.background = `rgba(255,255,255,${alpha.toFixed(3)})`;
    content.style.transform  = `translateY(${liftPx.toFixed(1)}px)`;
    content.style.opacity    = opacity.toFixed(3);
  }

  function onScrollOrResize() {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(updateFrame);
    }
  }

  // ------- Reveal quote when section is meaningfully visible -------
  let quoteShown = false;
  function revealQuoteSoon() {
    if (quoteShown || !quote) return;
    quoteShown = true;
    setTimeout(() => quote.classList.add('visible'), 350); // gentle delay
  }

  // ------- IntersectionObserver to toggle active state -------
  const io = ('IntersectionObserver' in window) ? new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.target !== section) continue;
        active = entry.isIntersecting;
        if (active) {
          revealQuoteSoon();
          onScrollOrResize(); // refresh immediately
          window.addEventListener('scroll', onScrollOrResize, { passive: true });
          window.addEventListener('resize', onScrollOrResize);
        } else {
          window.removeEventListener('scroll', onScrollOrResize);
          window.removeEventListener('resize', onScrollOrResize);
        }
      }
    },
    { root: null, threshold: [0, 0.2, 0.5, 1] }   // wake early, update through
  ) : null;

  if (io) {
    io.observe(section);
  } else {
    // Fallback for very old browsers: always-on listeners
    active = true;
    window.addEventListener('scroll', onScrollOrResize, { passive: true });
    window.addEventListener('resize', onScrollOrResize);
  }

  // Initial paint once the page is ready
  window.addEventListener('load', () => {
    onScrollOrResize();
    // If the section is already in view on load, show the quote
    const r = section.getBoundingClientRect();
    if (r.bottom > 0 && r.top < window.innerHeight) revealQuoteSoon();
  });

  // Optional: clean up on page hide (single-page apps)
  window.addEventListener('pagehide', () => {
    window.removeEventListener('scroll', onScrollOrResize);
    window.removeEventListener('resize', onScrollOrResize);
    if (io) io.disconnect();
  });
})();