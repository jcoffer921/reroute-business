document.addEventListener('DOMContentLoaded', () => {
  // Accordion behavior: one open at a time
  document.querySelectorAll('.la-acc-item').forEach(item => {
    const btn = item.querySelector('.la-acc-toggle');
    const panel = item.querySelector('.la-acc-panel');
    if (!btn || !panel) return;
    btn.addEventListener('click', () => {
      const isOpen = btn.getAttribute('aria-expanded') === 'true';
      document.querySelectorAll('.la-acc-toggle[aria-expanded="true"]').forEach(b => {
        if (b !== btn) {
          b.setAttribute('aria-expanded', 'false');
          const p = b.parentElement.querySelector('.la-acc-panel');
          if (p) p.hidden = true;
        }
      });
      btn.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
      panel.hidden = isOpen;
    });
  });
});
