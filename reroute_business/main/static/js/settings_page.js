(function(){
  document.addEventListener('DOMContentLoaded', function(){
    const navCards = document.querySelectorAll('.nav-card');
    const panels = document.querySelectorAll('.panel');

    const setActivePanel = (id, updateUrl) => {
      if (!id) return;
      navCards.forEach(b => b.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      const btn = Array.from(navCards).find(b => b.getAttribute('data-panel') === id);
      const panel = document.getElementById('panel-' + id);
      if (btn) btn.classList.add('active');
      if (panel) panel.classList.add('active');
      if (updateUrl && window.history && window.history.replaceState) {
        const url = new URL(window.location.href);
        url.searchParams.set('panel', id);
        window.history.replaceState({}, '', url.toString());
      }
    };

    navCards.forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-panel');
        setActivePanel(id, true);
      });
    });

    const panelParam = new URLSearchParams(window.location.search).get('panel');
    if (panelParam) setActivePanel(panelParam, false);

    const form = document.getElementById('recoveryForm');
    if (!form) return;
    const phoneInput = form.querySelector('#id_backup_phone');
    if (phoneInput) {
      phoneInput.addEventListener('input', () => {
        const digits = phoneInput.value.replace(/\D/g, '').slice(0, 10);
        const parts = [];
        if (digits.length > 0) parts.push('(' + digits.slice(0, Math.min(3, digits.length)) + (digits.length >= 3 ? ')' : ''));
        if (digits.length > 3) parts.push(' ' + digits.slice(3, Math.min(6, digits.length)));
        if (digits.length > 6) parts.push('-' + digits.slice(6));
        phoneInput.value = parts.join('');
      });
    }

    function showToast(msg) {
      const toast = document.createElement('div');
      toast.className = 'toast toast-success';
      toast.textContent = msg;
      document.body.appendChild(toast);
      setTimeout(() => { toast.classList.add('show'); }, 10);
      setTimeout(() => { toast.classList.remove('show'); toast.addEventListener('transitionend', () => toast.remove(), { once: true }); }, 2200);
    }

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const data = new URLSearchParams(new FormData(form));
      if (!data.get('update_recovery')) data.append('update_recovery', '1');
      const res = await fetch(window.location.href, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: data.toString(),
      }).catch(() => null);
      if (res && res.ok) {
        showToast('Recovery options saved');
      }
    });
  });
})();
