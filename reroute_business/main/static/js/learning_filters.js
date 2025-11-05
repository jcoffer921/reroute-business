(function(){
  var bar = document.querySelector('.video-filters');
  var grid = document.querySelector('.video-gallery-grid');
  if (!bar || !grid) return;

  function applyFilter(cat){
    grid.querySelectorAll('.learning-video-card').forEach(function(card){
      var c = (card.getAttribute('data-category')||'').toLowerCase();
      var ok = !cat || cat==='all' || c===cat;
      if (ok) card.removeAttribute('hidden'); else card.setAttribute('hidden','');
    });
  }

  bar.addEventListener('click', function(e){
    var a = e.target.closest('.filter-btn');
    if (!a) return;
    // Prevent navigation; filter client-side
    e.preventDefault();
    var url = new URL(a.href, window.location.origin);
    var cat = (url.searchParams.get('cat')||'').toLowerCase();
    bar.querySelectorAll('.filter-btn').forEach(function(b){ b.classList.remove('active'); });
    a.classList.add('active');
    applyFilter(cat||'all');
    // Update URL (no reload)
    var newUrl = cat ? (location.pathname + '?cat=' + encodeURIComponent(cat)) : location.pathname;
    history.replaceState(null, '', newUrl);
  });

  // Initial filter based on URL
  try{
    var cat0 = new URL(location.href).searchParams.get('cat')||'';
    applyFilter(cat0.toLowerCase()||'all');
  }catch(_){ applyFilter('all'); }
})();
