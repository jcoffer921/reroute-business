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
        if (p && typeof p.then === 'function') p.catch(()=>{
          // Retry after metadata/canplay or visibility change
        });
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
    document.body.classList.add('no-scroll');
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
    document.body.classList.remove('no-scroll');
    playBg();
  };

  // Hero play button opens modal with same hero video
  heroPlayBtn && heroPlayBtn.addEventListener('click', () => {
    var sourceEl = bgVideo ? bgVideo.querySelector('source') : null;
    const src = (bgVideo && bgVideo.currentSrc) || (sourceEl && sourceEl.src) || '';
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

  // Try to start background playback once handlers are wired up
  // (autoplay is allowed for muted video in most browsers)
  playBg();

  // Improve reliability: attempt again when media can play, and when tab becomes visible
  if (bgVideo) {
    bgVideo.addEventListener('loadeddata', () => {
      if (bgVideo.paused) playBg();
    });
    bgVideo.addEventListener('canplay', () => {
      if (bgVideo.paused) playBg();
    });
  }
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      if (bgVideo && bgVideo.paused) playBg();
    }
  });
})();

// Scroll reveal for feature sections
(function(){
  var revealTargets = document.querySelectorAll('.reveal-on-scroll');
  if (!revealTargets.length) return;

  if (!('IntersectionObserver' in window)) {
    revealTargets.forEach(function(el){ el.classList.add('is-visible'); });
    return;
  }

  var observer = new IntersectionObserver(function(entries, obs){
    entries.forEach(function(entry){
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      obs.unobserve(entry.target);
    });
  }, {
    threshold: 0.15,
    rootMargin: '0px 0px -8% 0px'
  });

  revealTargets.forEach(function(el){ observer.observe(el); });
})();

// Module completion handlers (HTML5 and YouTube) – CSP-safe
(function(){
  // HTML5 video completion messages
  document.querySelectorAll('.module-html5').forEach(function(v){
    v.addEventListener('ended', function(){
      var t = v.getAttribute('data-completion-target');
      if (t) {
        var el = document.getElementById(t);
        if (el) el.removeAttribute('hidden');
      }
    });
  });

  // YouTube iframe completion via Iframe API
  var ytIframes = document.querySelectorAll('iframe.yt-embed');
  if (ytIframes.length) {
    var tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    document.head.appendChild(tag);
    var prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = function(){
      if (typeof prev === 'function') { try { prev(); } catch(_){} }
      ytIframes.forEach(function(ifr){
        var completeId = ifr.getAttribute('data-completion-target') || '';
        // eslint-disable-next-line no-undef
        new YT.Player(ifr.id, {
          events: {
            onStateChange: function(e){
              try { if (typeof YT !== 'undefined' && e.data === YT.PlayerState.ENDED) {
                var el = document.getElementById(completeId);
                if (el) el.removeAttribute('hidden');
              } } catch(_){ }
            }
          }
        });
      });
    };
  }
})();
