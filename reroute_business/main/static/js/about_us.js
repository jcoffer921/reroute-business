// About Us page interactions: smooth anchor scroll
(function () {
  const cta = document.querySelector('.founders-cta');
  if (!cta) return;

  cta.addEventListener('click', (event) => {
    const targetId = cta.getAttribute('href');
    if (!targetId || targetId.charAt(0) !== '#') return;
    const target = document.querySelector(targetId);
    if (!target) return;

    event.preventDefault();
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    target.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
  });
})();
