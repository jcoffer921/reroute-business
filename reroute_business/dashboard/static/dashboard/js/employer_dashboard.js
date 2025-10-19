// Minimal JS to load applicants into a modal
(function () {
  const qs = (s, r = document) => r.querySelector(s);
  const qsa = (s, r = document) => Array.from(r.querySelectorAll(s));

  const modal = qs('#modalRoot');
  const backdrop = qs('#modalBackdrop');
  const body = qs('#modalBody');
  const closeBtn = modal ? modal.querySelector('.modal-close') : null;

  function openModal(html) {
    if (!modal || !backdrop) return;
    body.innerHTML = html || '';
    backdrop.classList.remove('hidden');
    modal.classList.remove('hidden');
  }

  function closeModal() {
    if (!modal || !backdrop) return;
    modal.classList.add('hidden');
    backdrop.classList.add('hidden');
    body.innerHTML = '';
  }

  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (backdrop) backdrop.addEventListener('click', closeModal);

  qsa('.view-applicants').forEach(btn => {
    btn.addEventListener('click', async () => {
      const url = btn.getAttribute('data-url');
      if (!url) return;
      try {
        body.textContent = 'Loading…';
        openModal();
        const resp = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        const html = await resp.text();
        body.innerHTML = html;
      } catch (e) {
        body.textContent = 'Failed to load applicants.';
      }
    });
  });

  // -------- Candidate autocomplete (employer schedule modal) --------
  const candInput = qs('#cand');
  const jobSelect = qs('#jobSelect');
  if (candInput) {
    // Create dropdown container
    const list = document.createElement('ul');
    list.className = 'list-group';
    list.style.position = 'absolute';
    list.style.zIndex = '100';
    list.style.background = '#fff';
    list.style.width = '100%';
    list.style.maxHeight = '200px';
    list.style.overflowY = 'auto';
    list.style.display = 'none';
    candInput.parentElement.style.position = 'relative';
    candInput.parentElement.appendChild(list);

    let timer = null;
    function hideList() { list.style.display = 'none'; }
    function showList() { list.style.display = list.children.length ? 'block' : 'none'; }

    async function fetchCandidates(q) {
      const url = new URL('/dashboard/employer/candidates/', window.location.origin);
      if (q) url.searchParams.set('q', q);
      const resp = await fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      if (!resp.ok) throw new Error('Network');
      return resp.json();
    }

    function render(items) {
      list.innerHTML = '';
      items.forEach(item => {
        const li = document.createElement('li');
        li.style.padding = '8px 10px';
        li.style.cursor = 'pointer';
        li.textContent = `${item.name} (@${item.username})`;
        li.addEventListener('mousedown', (e) => { // mousedown to beat blur
          e.preventDefault();
          candInput.value = item.username;
          hideList();
        });
        list.appendChild(li);
      });
      showList();
    }

    candInput.addEventListener('input', () => {
      const q = candInput.value.trim();
      clearTimeout(timer);
      timer = setTimeout(async () => {
        try {
          const data = await fetchCandidates(q);
          render((data && data.results) || []);
        } catch (e) {
          list.innerHTML = '';
          hideList();
        }
      }, 300);
    });
    candInput.addEventListener('blur', () => setTimeout(hideList, 150));
  }
})();
