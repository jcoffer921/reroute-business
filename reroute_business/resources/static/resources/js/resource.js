// Hero 2 video controls: background playback (modal removed)
(function(){
  const bgVideo = document.getElementById('hero2BgVideo');
  const modal = document.getElementById('hero2Modal');
  const modalVideo = document.getElementById('hero2ModalVideo');

  const playBg = () => {
    try {
      if (bgVideo) {
        bgVideo.muted = true;
        const p = bgVideo.play();
        if (p && typeof p.then === 'function') p.catch(()=>{});
      }
    } catch(_){}
  };

  // Start/maintain background playback regardless of modal presence
  playBg();
  if (bgVideo) {
    bgVideo.addEventListener('loadeddata', () => { if (bgVideo.paused) playBg(); });
    bgVideo.addEventListener('canplay', () => { if (bgVideo.paused) playBg(); });
  }
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) { if (bgVideo && bgVideo.paused) playBg(); }
  });

  // Legacy modal logic removed; keep no-op guards if DOM elements exist
  if (modal && modalVideo) {
    // If a downstream template still includes these, keep them hidden
    try { modal.setAttribute('hidden',''); } catch(_){}
  }
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
