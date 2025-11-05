// Microsoft-style gallery: click-to-play converts thumbnail to iframe with autoplay
(function(){
  var modal = document.getElementById('galleryVideoModal');
  var modalDialog = modal ? modal.querySelector('.hero2-modal-dialog') : null;
  var modalContainer = document.getElementById('galleryModalContainer');
  var closeBtn = document.getElementById('galleryModalClose');
  var fsBtn = document.getElementById('galleryModalFullscreen');

  function makeIframe(videoId){
    var ifr = document.createElement('iframe');
    ifr.className = 'yt-embed';
    ifr.setAttribute('allowfullscreen', '');
    ifr.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    ifr.setAttribute('title', 'YouTube video player');
    ifr.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share');
    ifr.src = 'https://www.youtube.com/embed/' + encodeURIComponent(videoId) + '?autoplay=1&rel=0&modestbranding=1&playsinline=1&enablejsapi=1';
    // Ensure it fills the modal container
    ifr.style.width = '100%';
    ifr.style.height = '100%';
    ifr.style.border = '0';
    return ifr;
  }

  function resetOverlays(){
    if (!modal) return;
    // Hide any legacy overlays or quiz containers from previous session
    modal.querySelectorAll('.lesson-overlay, .lesson-dialog, .lesson-complete').forEach(function(el){ el.hidden = true; el.setAttribute('aria-hidden','true'); });
    var qa = document.getElementById('galleryQuizActions'); if (qa) qa.hidden = true;
    var qc = document.getElementById('galleryQuizContainer'); if (qc) { qc.hidden = true; qc.innerHTML = ''; }
    var fb = modal.querySelector('.lesson-feedback'); if (fb) fb.textContent = '';
    var sum = modal.querySelector('.lesson-complete-summary'); if (sum) sum.textContent = '';
    // Clear previous answered state marker
    delete modal.__answered;
  }

  function openModal(){ if (modal) { resetOverlays(); modal.removeAttribute('hidden'); document.body.style.overflow='hidden'; } }
  function closeModal(){ if (modal) { modal.setAttribute('hidden',''); document.body.style.overflow=''; if (modalContainer){ modalContainer.innerHTML=''; }
      // Signal end of previous session
      modal.removeAttribute('data-iframe-id'); modal.removeAttribute('data-lesson');
    } }

  if (closeBtn){ closeBtn.addEventListener('click', closeModal); }
  document.addEventListener('click', function(e){ if (e.target && e.target.hasAttribute('data-gallery-close')) closeModal(); });
  if (fsBtn && modalDialog){
    fsBtn.addEventListener('click', function(){
      try{
        if (!document.fullscreenElement){ modalDialog.requestFullscreen && modalDialog.requestFullscreen(); }
        else { document.exitFullscreen && document.exitFullscreen(); }
      }catch(_){ }
    });
  }

  document.addEventListener('click', function(e){
    var btn = e.target.closest('.video-play-btn');
    if (!btn) return;
    e.preventDefault();
    var wrap = btn.closest('.video-thumb-container');
    if (!wrap) return;
    var vid = wrap.getAttribute('data-video-id');
    var mp4 = wrap.getAttribute('data-mp4-src');
    var card = wrap.closest('.learning-video-card');
    modalContainer && (modalContainer.innerHTML='');
    if (mp4){
      // Local MP4: use HTML5 video element
      var v = document.createElement('video');
      v.playsInline = true; v.setAttribute('playsinline','');
      v.autoplay = true; v.muted = false; v.controls = true; v.preload = 'metadata';
      v.style.width='100%'; v.style.height='100%'; v.style.objectFit='contain';
      var src = document.createElement('source'); src.src = mp4; src.type = 'video/mp4'; v.appendChild(src);
      if (modalContainer){ modalContainer.appendChild(v); }
      // Ensure no lesson data leaks into modal for plain MP4s
      if (modal){ modal.removeAttribute('data-lesson'); ['data-lesson-slug','data-schema-url','data-attempt-url','data-progress-url','data-iframe-id'].forEach(function(a){ modal.removeAttribute(a); }); }
      openModal();
      return;
    }

    if (!vid) return;
    // YouTube embed in modal
    var iframe = makeIframe(vid);
    var autoId = 'ytvid-' + Math.random().toString(36).slice(2,10);
    iframe.id = autoId;
    if (modalContainer){ modalContainer.appendChild(iframe); }

    if (card && modal){
      if (card.hasAttribute('data-lesson')) modal.setAttribute('data-lesson','1'); else modal.removeAttribute('data-lesson');
      ['data-lesson-slug','data-schema-url','data-attempt-url','data-progress-url'].forEach(function(attr){
        var vAttr = card.getAttribute(attr);
        if (vAttr) modal.setAttribute(attr, vAttr); else modal.removeAttribute(attr);
      });
      modal.setAttribute('data-iframe-id', autoId);
    }

    openModal();
  });
})();
