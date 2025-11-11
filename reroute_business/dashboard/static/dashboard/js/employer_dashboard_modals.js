(function(){
  var openBtn = document.getElementById('openScheduleInterview');
  var modal = document.getElementById('scheduleInterviewModal');
  var backdrop = document.getElementById('scheduleInterviewBackdrop');
  var closeBtn = document.getElementById('scheduleInterviewClose');
  function open(){ if(modal&&backdrop){ modal.classList.remove('hidden'); backdrop.classList.remove('hidden'); } }
  function close(){ if(modal&&backdrop){ modal.classList.add('hidden'); backdrop.classList.add('hidden'); } }
  if (openBtn) openBtn.addEventListener('click', open);
  if (backdrop) backdrop.addEventListener('click', close);
  if (closeBtn) closeBtn.addEventListener('click', close);
  var closeBtn2 = document.getElementById('scheduleInterviewClose2');
  if (closeBtn2) closeBtn2.addEventListener('click', close);
})();

(function(){
  document.addEventListener('click', function(e){
    var toggle = e.target.closest('.dropdown-toggle');
    if (!toggle && !e.target.closest('.actions-dropdown')) {
      document.querySelectorAll('.actions-dropdown .dropdown-menu').forEach(function(m){ m.classList.remove('show'); });
      return;
    }
    if (toggle) {
      var id = toggle.getAttribute('data-menu-id');
      var menu = document.getElementById(id);
      if (menu) {
        var isOpen = menu.classList.contains('show');
        document.querySelectorAll('.actions-dropdown .dropdown-menu').forEach(function(m){ m.classList.remove('show'); });
        if (!isOpen) menu.classList.add('show');
      }
    }
  });

  var openBtns = document.querySelectorAll('.openReschedule');
  var modal = document.getElementById('rescheduleInterviewModal');
  var backdrop = document.getElementById('rescheduleInterviewBackdrop');
  var closeBtn = document.getElementById('rescheduleInterviewClose');
  var closeBtn2 = document.getElementById('rescheduleInterviewClose2');
  var idInput = document.getElementById('rescheduleInterviewId');
  var dtInput = document.getElementById('rescheduleDt');

  function open(interviewId, dt){
    if (!modal) return;
    if (idInput) idInput.value = interviewId || '';
    if (dt && dtInput) dtInput.value = dt;
    modal.classList.remove('hidden');
    backdrop && backdrop.classList.remove('hidden');
    document.querySelectorAll('.actions-dropdown .dropdown-menu').forEach(function(m){ m.classList.remove('show'); });
  }
  function close(){ if (!modal) return; modal.classList.add('hidden'); backdrop && backdrop.classList.add('hidden'); }

  openBtns.forEach(function(btn){
    btn.addEventListener('click', function(){
      var id = btn.getAttribute('data-interview');
      var dt = btn.getAttribute('data-datetime');
      open(id, dt);
    });
  });
  if (backdrop) backdrop.addEventListener('click', close);
  if (closeBtn) closeBtn.addEventListener('click', close);
  if (closeBtn2) closeBtn2.addEventListener('click', close);
  document.addEventListener('keydown', function(e){ if(e.key==='Escape') close(); });
})();

