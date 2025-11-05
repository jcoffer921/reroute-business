// Microsoft-style gallery: click-to-play converts thumbnail to iframe with autoplay
(function(){
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

  document.addEventListener('click', function(e){
    var btn = e.target.closest('.video-play-btn');
    if (!btn) return;
    e.preventDefault();
    var wrap = btn.closest('.video-thumb-container');
    if (!wrap) return;
    var vid = wrap.getAttribute('data-video-id');
    if (!vid) return;
    var card = wrap.closest('.learning-video-card');

    // Replace thumb with iframe
    var iframe = makeIframe(vid);
    // Give the iframe a stable id for gallery_lessons.js to hook if needed
    var autoId = 'ytvid-' + Math.random().toString(36).slice(2,10);
    iframe.id = autoId;
    wrap.replaceWith(iframe);
  });
})();

