(function(){
  const btn = document.getElementById('backToTopBtn');
  if (!btn) return;
  const onScroll = () => {
    const y = window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
    if (y > 200) btn.removeAttribute('hidden'); else btn.setAttribute('hidden','');
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
})();

