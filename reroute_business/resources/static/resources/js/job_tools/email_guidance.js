(function(){
  function copyText(el) {
    const code = el.textContent.trim();
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(code);
    } else {
      const ta = document.createElement('textarea');
      ta.value = code; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } finally { document.body.removeChild(ta); }
      return Promise.resolve();
    }
  }

  document.querySelectorAll('.eg-copy').forEach(btn => {
    btn.addEventListener('click', () => {
      const sel = btn.getAttribute('data-copy-target');
      const target = document.querySelector(sel);
      if (!target) return;
      copyText(target).then(() => {
        const original = btn.textContent;
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = original; }, 1400);
      });
    });
  });
})();

