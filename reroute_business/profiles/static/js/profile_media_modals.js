// Background image modal behavior (owner view)
(function () {
  const bgModal = document.getElementById('bgModal');
  if (!bgModal) return;

  const bgInput = document.getElementById('bgFileInput');
  const bgPreview = document.getElementById('bgPreview');
  const triggers = Array.from(document.querySelectorAll('[data-open-bg]'));
  const closeButtons = Array.from(bgModal.querySelectorAll('[data-close-bg]'));
  let lastFocused = null;
  let bgObjectURL = null;

  const cleanupModalArtifacts = () => {
    document.body.classList.remove('modal-open');
    const backdrops = document.querySelectorAll('.modal-backdrop');
    if (backdrops.length) backdrops.forEach((el) => el.remove());
  };

  const openBg = () => {
    if (!bgModal.hasAttribute('hidden')) return;
    lastFocused = document.activeElement;
    cleanupModalArtifacts();
    bgModal.removeAttribute('hidden');
    bgModal.setAttribute('aria-hidden', 'false');
    const focusTarget = bgModal.querySelector('input, button, [href], select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusTarget) focusTarget.focus({ preventScroll: true });
  };

  const closeBg = () => {
    if (bgModal.hasAttribute('hidden')) return;
    bgModal.setAttribute('hidden', '');
    bgModal.setAttribute('aria-hidden', 'true');
    cleanupModalArtifacts();
    if (lastFocused && document.contains(lastFocused)) {
      lastFocused.focus({ preventScroll: true });
    }
  };

  triggers.forEach((trigger) => {
    trigger.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      openBg();
    });
    trigger.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openBg();
      }
    });
  });

  bgModal.addEventListener('click', (e) => {
    if (e.target === bgModal) closeBg();
  });

  closeButtons.forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      closeBg();
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !bgModal.hasAttribute('hidden')) {
      e.preventDefault();
      closeBg();
    }
  });

  if (bgInput && bgPreview) {
    bgInput.addEventListener('change', () => {
      const file = bgInput.files && bgInput.files[0];
      if (!file) {
        bgPreview.setAttribute('hidden', '');
        return;
      }
      if (bgObjectURL) URL.revokeObjectURL(bgObjectURL);
      bgObjectURL = URL.createObjectURL(file);
      bgPreview.src = bgObjectURL;
      bgPreview.removeAttribute('hidden');
    });
  }
})();
