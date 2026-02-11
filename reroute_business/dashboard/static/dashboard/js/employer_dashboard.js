(function(){
  document.addEventListener('DOMContentLoaded', function(){
    var sel = document.getElementById('sort_by');
    if (sel && sel.form){ sel.addEventListener('change', function(){ sel.form.submit(); }); }

    var shell = document.querySelector('[data-employer-shell]');
    var toggle = document.querySelector('[data-sidebar-toggle]');
    var backdrop = document.querySelector('[data-sidebar-backdrop]');

    function closeSidebar() {
      if (shell) { shell.classList.remove('is-sidebar-open'); }
    }

    if (toggle && shell) {
      toggle.addEventListener('click', function(){
        shell.classList.toggle('is-sidebar-open');
      });
    }

    if (backdrop) {
      backdrop.addEventListener('click', closeSidebar);
    }

    document.addEventListener('keydown', function(event){
      if (event.key === 'Escape') { closeSidebar(); }
    });

    var stageSelects = document.querySelectorAll('[data-stage-select]');
    stageSelects.forEach(function(select){
      var targetId = select.getAttribute('data-stage-target');
      var target = targetId ? document.getElementById(targetId) : null;
      select.addEventListener('change', function(){
        if (target) {
          target.textContent = select.options[select.selectedIndex].text;
        }
      });
    });
  });
})();
