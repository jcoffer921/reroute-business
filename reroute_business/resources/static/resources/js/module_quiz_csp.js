// CSP-safe module quiz renderer: fetch schema and build DOM
(function(){
  function ready(fn){ if(document.readyState !== 'loading') fn(); else document.addEventListener('DOMContentLoaded', fn); }
  function getCookie(name){
    var value = '; ' + document.cookie;
    var parts = value.split('; ' + name + '=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  }

  function formatTimestamp(value){
    if (!value) return '';
    try {
      var date = new Date(value);
      if (!isNaN(date.getTime())){
        return date.toLocaleString();
      }
    } catch (err){
      return '';
    }
    return '';
  }

  function showMessage(el, text){
    if (!el) return;
    el.textContent = text;
  }

  function updateStatusDisplay(score, total, updatedAt){
    var status = document.querySelector('.quiz-status');
    if (!status) return;
    var label = status.querySelector('.quiz-status__label');
    if (!label){
      label = document.createElement('div');
      label.className = 'quiz-status__label';
      status.insertBefore(label, status.firstChild);
    }
    label.textContent = 'Latest Score';

    var value = status.querySelector('.quiz-status__value');
    if (!value){
      value = document.createElement('div');
      value.className = 'quiz-status__value';
      status.insertBefore(value, label.nextSibling);
    }
    value.textContent = score + ' / ' + total;

    var meta = status.querySelector('.quiz-status__meta');
    if (!meta){
      meta = document.createElement('div');
      meta.className = 'quiz-status__meta';
      status.appendChild(meta);
    }
    meta.textContent = updatedAt ? ('Updated ' + updatedAt) : '';
  }

  ready(function(){
    var root = document.getElementById('quizPanel');
    var submit = document.getElementById('quizSubmit');
    var resultEl = document.getElementById('quizResult');
    if (!root || !submit) return;

    var schemaUrl = root.getAttribute('data-quiz-url');
    var submitUrl = root.getAttribute('data-submit-url') || submit.getAttribute('data-submit-url');
    var canSubmit = root.getAttribute('data-can-submit') === 'true';
    if (!schemaUrl){
      root.textContent = 'No quiz found for this module.';
      return;
    }

    var schema = null;

    fetch(schemaUrl, { credentials: 'same-origin' })
      .then(function(response){
        if (!response.ok) throw new Error('Failed to load quiz schema.');
        return response.json();
      })
      .then(function(data){
        schema = data || {};
        render(schema);
        if (schema.user_score){
          var stamp = formatTimestamp(schema.user_score.updated_at);
          updateStatusDisplay(schema.user_score.score, schema.user_score.total_questions, stamp);
        }
      })
      .catch(function(){
        root.textContent = 'Unable to load quiz.';
      });

    function render(sc){
      var qs = Array.isArray(sc.questions) ? sc.questions : [];
      root.innerHTML = '';
      if (!qs.length){
        var empty = document.createElement('div');
        empty.className = 'quiz-q';
        empty.textContent = 'No quiz available for this module.';
        root.appendChild(empty);
        return;
      }

      qs.forEach(function(q){
        var box = document.createElement('div');
        box.className = 'quiz-q';

        var h = document.createElement('h4');
        h.textContent = q.prompt || '';
        box.appendChild(h);

        var list = document.createElement('div');
        list.className = 'quiz-choices';

        (q.choices || []).forEach(function(choice){
          var id = 'q' + q.id + '_' + choice.id;
          var label = document.createElement('label');
          label.setAttribute('for', id);

          var input = document.createElement('input');
          input.type = 'radio';
          input.name = 'q_' + q.id;
          input.value = choice.id;
          input.id = id;

          var span = document.createElement('span');
          span.textContent = choice.text || '';

          label.appendChild(input);
          label.appendChild(span);
          list.appendChild(label);
        });

        box.appendChild(list);
        root.appendChild(box);
      });

      if (canSubmit){
        submit.addEventListener('click', function(){
          handleSubmit(qs);
        }, { once: false });
      }
    }

    function handleSubmit(questions){
      if (!Array.isArray(questions) || !questions.length){
        showMessage(resultEl, 'Quiz is still loading.');
        return;
      }

      var answers = [];
      var total = questions.length;
      var correct = 0;
      var attempted = 0;

      questions.forEach(function(q){
        var selected = document.querySelector('input[name="q_' + q.id + '"]:checked');
        if (!selected) return;
        attempted += 1;
        var value = selected.value;
        var choice = (q.choices || []).find(function(c){ return String(c.id) === String(value); });
        if (choice && (choice.is_correct === true || choice.correct === true)){
          correct += 1;
        }
        answers.push({
          question_id: q.id,
          answer_id: value
        });
      });

      showMessage(resultEl, 'You answered ' + correct + ' of ' + attempted + ' attempted questions correctly.');

      if (!submitUrl){
        return;
      }

      var csrf = getCookie('csrftoken');
      var headers = { 'Content-Type': 'application/json' };
      if (csrf){
        headers['X-CSRFToken'] = csrf;
      }

      fetch(submitUrl, {
        method: 'POST',
        headers: headers,
        credentials: 'same-origin',
        body: JSON.stringify({
          answers: answers,
          total: total,
          score: correct
        }),
      })
        .then(function(response){
          if (!response.ok){
            return response.json().catch(function(){ return {}; }).then(function(body){
              var message = body.error || 'Unable to save score.';
              throw new Error(message);
            });
          }
          return response.json();
        })
        .then(function(payload){
          var serverScore = typeof payload.score === 'number' ? payload.score : correct;
          var serverTotal = typeof payload.total_questions === 'number' ? payload.total_questions : total;
          var percent;
          if (typeof payload.percent === 'number'){
            percent = payload.percent;
          } else if (serverTotal) {
            percent = Math.round((serverScore / serverTotal) * 100);
          } else {
            percent = 0;
          }
          var updatedText = payload.updated_at ? formatTimestamp(payload.updated_at) : 'just now';
          var msg = (payload.message || 'Score saved.') + ' (' + serverScore + '/' + serverTotal + ', ' + percent + '%)';
          showMessage(resultEl, msg);
          updateStatusDisplay(serverScore, serverTotal, updatedText);
        })
        .catch(function(err){
          showMessage(resultEl, err.message || 'Unable to save score.');
        });
    }
  });
})();
