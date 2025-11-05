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
    return ifr;
  }

  function openModal(){ if (modal) { modal.removeAttribute('hidden'); document.body.style.overflow='hidden'; } }
  function closeModal(){ if (modal) { modal.setAttribute('hidden',''); document.body.style.overflow=''; if (modalContainer){ modalContainer.innerHTML=''; } } }

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
    if (!vid) return;
    var card = wrap.closest('.learning-video-card');

    // Open modal with iframe
    var iframe = makeIframe(vid);
    var autoId = 'ytvid-' + Math.random().toString(36).slice(2,10);
    iframe.id = autoId;
    if (modalContainer){ modalContainer.innerHTML=''; modalContainer.appendChild(iframe); }

    // Propagate lesson attributes to modal so gallery_lessons.js can attach
    if (card && modal){
      if (card.hasAttribute('data-lesson')) modal.setAttribute('data-lesson','1'); else modal.removeAttribute('data-lesson');
      ['data-lesson-slug','data-schema-url','data-attempt-url','data-progress-url'].forEach(function(attr){
        var v = card.getAttribute(attr);
        if (v) modal.setAttribute(attr, v); else modal.removeAttribute(attr);
      });
      // Also tag iframe id onto modal in case controller needs it
      modal.setAttribute('data-iframe-id', autoId);
    }

    openModal();
  });
})();
