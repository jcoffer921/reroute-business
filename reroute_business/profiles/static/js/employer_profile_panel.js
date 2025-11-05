(function(){
  document.addEventListener('DOMContentLoaded', function(){
    const openBtn = document.getElementById('openEditPanel');
    const panel = document.getElementById('editPanel');
    const closeBtn = document.getElementById('closeEditPanel');
    const cancelInside = document.getElementById('cancelInside');
    const open = function(){ if(!panel) return; panel.classList.remove('hidden'); panel.classList.add('active'); panel.setAttribute('aria-hidden','false'); };
    const close = function(){ if(!panel) return; panel.classList.remove('active'); panel.classList.add('hidden'); panel.setAttribute('aria-hidden','true'); };
    if (openBtn) openBtn.addEventListener('click', open);
    document.querySelectorAll('[data-open-edit]').forEach(function(b){ b.addEventListener('click', open); });
    if (closeBtn) closeBtn.addEventListener('click', close);
    if (cancelInside) cancelInside.addEventListener('click', close);
    document.addEventListener('keydown', function(e){ if(e.key==='Escape') close(); });
  });
})();

