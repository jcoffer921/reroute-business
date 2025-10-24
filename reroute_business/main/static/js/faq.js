document.addEventListener('DOMContentLoaded', () => {
  const search = document.getElementById('faqSearch');
  const items = Array.from(document.querySelectorAll('.faq-item'));

  // Accordion behavior
  document.body.addEventListener('click', (e) => {
    const btn = e.target.closest('.faq-q');
    if (!btn) return;
    const expanded = btn.getAttribute('aria-expanded') === 'true';
    const answer = btn.parentElement.querySelector('.faq-a');
    btn.setAttribute('aria-expanded', String(!expanded));
    if (answer) {
      if (expanded) {
        answer.hidden = true;
      } else {
        answer.hidden = false;
      }
    }
  });

  // Search filter
  if (search) {
    search.addEventListener('input', () => {
      const q = search.value.trim().toLowerCase();
      items.forEach((it) => {
        const text = it.querySelector('.faq-q span')?.textContent?.toLowerCase() || '';
        const body = it.querySelector('.faq-a')?.textContent?.toLowerCase() || '';
        const match = !q || text.includes(q) || body.includes(q);
        it.style.display = match ? '' : 'none';
      });
    });
  }
});

