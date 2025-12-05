(function(){
  var bar = document.querySelector('.video-filters');
  var grid = document.querySelector('.video-gallery-grid');
  var search = document.querySelector('#video-search');
  if (!bar || !grid) return;

  var activeCat = null;

  function applyFilter(cat, term){
    activeCat = cat;
    var t = (term || '').trim().toLowerCase();
    grid.querySelectorAll('.learning-video-card').forEach(function(card){
      var c = (card.getAttribute('data-category')||'').toLowerCase();
      var tags = (card.getAttribute('data-tags')||'').toLowerCase();
      var title = (card.getAttribute('data-title')||'').toLowerCase();
      var catOk = !cat || cat==='all' || c===cat;
      var searchOk = !t || (tags + ' ' + title).indexOf(t) !== -1;
      if (catOk && searchOk) card.removeAttribute('hidden'); else card.setAttribute('hidden','');
    });
  }

  bar.addEventListener('click', function(e){
    var a = e.target.closest('.filter-btn');
    if (!a) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    // Prevent navigation; filter client-side
    e.preventDefault();
    var url = new URL(a.href, window.location.origin);
    var cat = (url.searchParams.get('cat')||'').toLowerCase();
    bar.querySelectorAll('.filter-btn').forEach(function(b){ b.classList.remove('active'); });
    a.classList.add('active');
    applyFilter(cat||'all', search ? search.value : '');
    // Update URL (no reload)
    var newUrl = cat ? (location.pathname + '?cat=' + encodeURIComponent(cat)) : location.pathname;
    history.replaceState(null, '', newUrl);
  });

  // Initial filter based on URL
  try{
    var cat0 = new URL(location.href).searchParams.get('cat')||'';
    applyFilter(cat0.toLowerCase()||'all', search ? search.value : '');
  }catch(_){ applyFilter('all', search ? search.value : ''); }

  if (search){
    search.addEventListener('input', function(){
      applyFilter(activeCat || 'all', search.value);
    });
  }
})();
