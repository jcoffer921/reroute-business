(function(){
  function getCSRFToken() {
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function showToast(msg, kind) {
    const t = document.createElement('div');
    t.className = `toast ${kind === 'error' ? 'toast-error' : 'toast-success'}`;
    t.textContent = msg;
    document.body.appendChild(t);
    requestAnimationFrame(()=> t.classList.add('show'));
    setTimeout(()=>{
      t.classList.remove('show');
      t.addEventListener('transitionend', ()=> t.remove(), { once: true });
    }, 2000);
  }

  async function postForm(form) {
    const fd = new FormData(form);
    const res = await fetch(form.action, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCSRFToken(),
      },
      body: fd,
      credentials: 'same-origin'
    });
    let data = null;
    try { data = await res.json(); } catch(_) {}
    return { ok: res.ok, data };
  }

  document.addEventListener('submit', async (e) => {
    const form = e.target;
    if (!(form.classList.contains('js-archive-form') || form.classList.contains('js-unarchive-form'))) return;
    e.preventDefault();
    const card = form.closest('.saved-job-card');
    const { ok } = await postForm(form);
    if (ok) {
      if (card) card.remove();
      showToast(form.classList.contains('js-archive-form') ? 'Job archived' : 'Moved back to Saved');
    } else {
      showToast('Action failed', 'error');
    }
  });
})();

