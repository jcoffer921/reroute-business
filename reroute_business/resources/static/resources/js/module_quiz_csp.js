// CSP-safe module quiz renderer: fetch schema and build DOM
(function(){
  function ready(fn){ if(document.readyState !== 'loading') fn(); else document.addEventListener('DOMContentLoaded', fn); }
  ready(function(){
    var root = document.getElementById('quizPanel');
    var submit = document.getElementById('quizSubmit');
    var resultEl = document.getElementById('quizResult');
    if (!root || !submit) return;

    var url = root.getAttribute('data-quiz-url');
    if (!url) { root.innerHTML = '<div class="quiz-q">No quiz found for this module.</div>'; return; }

    var schema = null;
    fetch(url, { credentials: 'same-origin' })
      .then(function(r){ return r.ok ? r.json() : {}; })
      .then(function(data){ schema = data || {}; render(schema); })
      .catch(function(){ root.innerHTML = '<div class="quiz-q">Unable to load quiz.</div>'; });

    function render(sc){
      var qs = (sc && sc.questions) || [];
      root.innerHTML = '';
      if (!qs.length){ root.innerHTML = '<div class="quiz-q">No quiz available for this module.</div>'; return; }
      qs.forEach(function(q){
        var box = document.createElement('div'); box.className = 'quiz-q';
        var h = document.createElement('h4'); h.textContent = q.prompt || ''; box.appendChild(h);
        var list = document.createElement('div'); list.className = 'quiz-choices';
        (q.choices || []).forEach(function(ch){
          var id = 'q' + q.id + '_' + ch.id;
          var lab = document.createElement('label'); lab.setAttribute('for', id);
          var inp = document.createElement('input'); inp.type = 'radio'; inp.name = 'q_' + q.id; inp.value = ch.id; inp.id = id;
          var span = document.createElement('span'); span.textContent = ch.text || '';
          lab.appendChild(inp); lab.appendChild(span); list.appendChild(lab);
        });
        box.appendChild(list); root.appendChild(box);
      });

      submit.onclick = function(){
        var total = 0, correct = 0;
        qs.forEach(function(q){
          var sel = document.querySelector('input[name="q_' + q.id + '"]:checked');
          if (!sel) return;
          total++;
          var picked = String(sel.value);
          var match = (q.choices || []).find(function(c){ return String(c.id) === picked; });
          if (match && (match.is_correct === true || match.correct === true)) correct++;
        });
        if (resultEl) resultEl.textContent = 'You answered ' + correct + ' of ' + total + ' correctly.';
      };
    }
  });
})();

