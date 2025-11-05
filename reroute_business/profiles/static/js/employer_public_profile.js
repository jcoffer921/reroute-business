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
    // Discretize to 0..10, add class on root for CSS-driven transforms
    const step = Math.min(10, Math.max(0, Math.round(progress * 10)));
    for (let i=0;i<=10;i++){ root.classList.remove('parallax-step-'+i); }
    root.classList.add('parallax-step-'+step);
  };

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  onScroll();
})();
