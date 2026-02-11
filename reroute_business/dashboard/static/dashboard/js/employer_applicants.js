(function(){
  document.addEventListener('DOMContentLoaded', function(){
    function getCsrfToken() {
      var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
      return match ? match[1] : '';
    }

    var toggles = document.querySelectorAll('[data-notes-toggle]');
    toggles.forEach(function(toggle){
      toggle.addEventListener('click', function(){
        var card = toggle.closest('.applicant-card');
        if (!card) return;
        var panel = card.querySelector('[data-notes-panel]');
        if (!panel) return;
        var isOpen = panel.classList.toggle('is-open');
        toggle.textContent = isOpen ? 'Edit Notes' : '+ Add Notes';
      });
    });

    var cancelButtons = document.querySelectorAll('[data-notes-cancel]');
    cancelButtons.forEach(function(button){
      button.addEventListener('click', function(){
        var card = button.closest('.applicant-card');
        if (!card) return;
        var panel = card.querySelector('[data-notes-panel]');
        var toggle = card.querySelector('[data-notes-toggle]');
        if (panel) panel.classList.remove('is-open');
        if (toggle) toggle.textContent = '+ Add Notes';
      });
    });

    var statusSelects = document.querySelectorAll('[data-status-select]');
    statusSelects.forEach(function(select){
      select.addEventListener('change', function(){
        var url = select.getAttribute('data-status-url');
        if (!url) return;
        var formData = new FormData();
        formData.append('status', select.value);
        fetch(url, {
          method: 'POST',
          headers: { 'X-CSRFToken': getCsrfToken() },
          body: formData
        }).then(function(response){
          if (!response.ok) {
            throw new Error('Request failed');
          }
        }).catch(function(){
          select.value = select.getAttribute('data-prev') || select.value;
        });
      });
      select.addEventListener('focus', function(){
        select.setAttribute('data-prev', select.value);
      });
    });

    var saveButtons = document.querySelectorAll('[data-notes-save]');
    saveButtons.forEach(function(button){
      button.addEventListener('click', function(){
        var card = button.closest('.applicant-card');
        if (!card) return;
        var textarea = card.querySelector('[data-notes-field]');
        var url = button.getAttribute('data-notes-url');
        if (!textarea || !url) return;
        var formData = new FormData();
        formData.append('notes', textarea.value);
        fetch(url, {
          method: 'POST',
          headers: { 'X-CSRFToken': getCsrfToken() },
          body: formData
        }).then(function(response){
          if (!response.ok) {
            throw new Error('Request failed');
          }
          return response.json();
        }).then(function(){
          var panel = card.querySelector('[data-notes-panel]');
          var toggle = card.querySelector('[data-notes-toggle]');
          if (panel) panel.classList.remove('is-open');
          if (toggle) {
            toggle.textContent = textarea.value.trim() ? 'Edit Notes' : '+ Add Notes';
          }
        });
      });
    });
  });
})();
