// Subtle parallax + fade on hero background
(function() {
  const root = document.querySelector('.employer-public');
  if (!root) return;
  const hero = root.querySelector('.hero');
  const bg = root.querySelector('.hero-bg');
  const wm = root.querySelector('.hero-watermark');
  if (!hero || !bg) return;

  const onScroll = () => {
    const rect = hero.getBoundingClientRect();
    const h = rect.height || hero.offsetHeight || 1;
    const scrolled = Math.min(Math.max(-rect.top, 0), h);
    const progress = scrolled / h; // 0 -> 1
    // Parallax translate + subtle fade
    const translate = progress * 20; // px
    const opacity = 1 - progress * 0.35; // fade to ~0.65
    bg.style.transform = `translateY(${translate}px)`;
    bg.style.opacity = String(opacity);
    if (wm) {
      wm.style.transform = `translateY(${translate * 0.7}px)`;
      wm.style.opacity = String(0.12 * (1 - progress * 0.5));
    }
  };

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  onScroll();
})();
