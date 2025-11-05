(function(){
  document.addEventListener('DOMContentLoaded', function(){
    var sel = document.getElementById('sort_by');
    if (sel && sel.form){ sel.addEventListener('change', function(){ sel.form.submit(); }); }
  });
})();

