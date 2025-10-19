(function(){
  const items = document.querySelectorAll('.acc-item');
  items.forEach(item => {
    const btn = item.querySelector('.acc-toggle');
    const panel = item.querySelector('.acc-panel');
    if (!btn || !panel) return;
    btn.addEventListener('click', () => {
      const open = btn.getAttribute('aria-expanded') === 'true';
      // Close others in the group for a clean UX
      document.querySelectorAll('.acc-toggle[aria-expanded="true"]').forEach(b => {
        if (b !== btn) {
          b.setAttribute('aria-expanded','false');
          const p = b.parentElement.querySelector('.acc-panel');
          if (p) p.hidden = true;
        }
      });
      btn.setAttribute('aria-expanded', open ? 'false' : 'true');
      panel.hidden = open;
    });
  });
})();

