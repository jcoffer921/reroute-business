// Hero 2 video controls: background playback + modal playback
(function(){
  const bgVideo = document.getElementById('hero2BgVideo');
  const heroPlayBtn = document.getElementById('hero2Play');
  const modal = document.getElementById('hero2Modal');
  const modalVideo = document.getElementById('hero2ModalVideo');
  const closeBtn = document.getElementById('hero2Close');

  if (!modal || !modalVideo) return;

  const playBg = () => {
    try {
      if (bgVideo) {
        bgVideo.muted = true;
        const p = bgVideo.play();
        if (p && typeof p.then === 'function') p.catch(()=>{});
      }
    } catch(_){}
  };

  const pauseBg = () => { try { if (bgVideo) bgVideo.pause(); } catch(_){} };

  const openModalWithSrc = (src) => {
    pauseBg();
    if (src) {
      try {
        modalVideo.pause();
        modalVideo.removeAttribute('src');
        modalVideo.src = src;
        modalVideo.load();
      } catch(_){}
    }
    modal.removeAttribute('hidden');
    document.body.style.overflow = 'hidden';
    try {
      modalVideo.muted = false;
      modalVideo.controls = true;
      const p = modalVideo.play();
      if (p && typeof p.then === 'function') { p.catch(()=>{}); }
    } catch(_){}
  };

  const closeModal = () => {
    try { modalVideo.pause(); } catch(_){}
    modal.setAttribute('hidden', '');
    document.body.style.overflow = '';
    playBg();
  };

  // Hero play button opens modal with same hero video
  heroPlayBtn && heroPlayBtn.addEventListener('click', () => {
    const src = (bgVideo && bgVideo.currentSrc) || (bgVideo && bgVideo.querySelector('source')?.src) || '';
    openModalWithSrc(src);
  });

  // Generic openers for video cards
  document.querySelectorAll('[data-video-open]').forEach(btn => {
    btn.addEventListener('click', () => {
      const src = btn.getAttribute('data-video-src');
      openModalWithSrc(src);
    });
  });

  closeBtn && closeBtn.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => {
    if (e.target && e.target.hasAttribute('data-hero2-close')) closeModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modal.hasAttribute('hidden')) closeModal();
  });
})();
