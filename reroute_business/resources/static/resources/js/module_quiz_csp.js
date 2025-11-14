// Modern guided quiz flow (CSP-safe, no inline scripts)
(function(){
  function ready(fn){
    if (document.readyState !== 'loading'){ fn(); }
    else { document.addEventListener('DOMContentLoaded', fn); }
  }

  function getCookie(name){
    var value = '; ' + document.cookie;
    var parts = value.split('; ' + name + '=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  }

  function formatTimestamp(value){
    if (!value) return '';
    var date = new Date(value);
    if (isNaN(date.getTime())) return '';
    return date.toLocaleString();
  }

  function clamp(value, min, max){
    return Math.min(Math.max(value, min), max);
  }

  ready(function(){
    var quizRoot = document.getElementById('quizFlow');
    if (!quizRoot) return;

    var questionStage = document.getElementById('quizQuestionStage');
    var progressLabel = document.getElementById('quizProgressLabel');
    var progressFill = document.getElementById('quizProgressFill');
    var prevBtn = document.getElementById('quizPrevBtn');
    var nextBtn = document.getElementById('quizNextBtn');
    var submitBtn = document.getElementById('quizSubmitBtn');
    var completeBtn = document.getElementById('quizCompleteBtn');
    var resultCard = document.getElementById('quizResultCard');
    var startBtn = document.getElementById('quizStartBtn');
    var inlineStartBtn = document.getElementById('quizInlineStartBtn');
    var lockScreen = document.getElementById('quizLockScreen');
    var retakeBtn = document.getElementById('quizRetakeBtn');
    var confettiHost = document.getElementById('quizConfetti');
    var quizSection = document.getElementById('quizSection');

    var schemaUrl = quizRoot.getAttribute('data-quiz-url');
    var submitUrl = quizRoot.getAttribute('data-submit-url');
    var canSubmit = quizRoot.getAttribute('data-can-submit') === 'true';
    var moduleId = quizRoot.getAttribute('data-module-id');

    if (!schemaUrl){
      if (questionStage) questionStage.textContent = 'No quiz available for this module.';
      return;
    }

    var state = {
      questions: [],
      current: 0,
      answers: {},
      evaluation: {},
      hasSubmitted: false,
      latestScore: null,
    };
    var isUnlocked = false;

    function unlockQuiz(){
      if (isUnlocked) return;
      isUnlocked = true;
      quizRoot.classList.remove('quiz-flow--locked');
      quizRoot.setAttribute('data-state', 'active');
      if (lockScreen){
        lockScreen.style.display = 'none';
      }
      renderQuestion();
    }

    function handleStartClick(){
      unlockQuiz();
      if (quizSection){
        quizSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }

    if (startBtn){
      startBtn.addEventListener('click', handleStartClick);
    }
    if (inlineStartBtn){
      inlineStartBtn.addEventListener('click', handleStartClick);
    }

    if (completeBtn && moduleId){
      var key = 'module_complete_' + moduleId;
      try {
        if (localStorage.getItem(key) === 'done'){
          markCompleteUI(true);
        }
      } catch (err){}
      completeBtn.addEventListener('click', function(){
        if (completeBtn.getAttribute('data-complete') === 'true') return;
        completeBtn.setAttribute('data-complete', 'true');
        completeBtn.textContent = 'Module marked complete ✓';
        completeBtn.classList.add('is-complete');
        try { localStorage.setItem(key, 'done'); } catch (err){}
        showResult('Module marked complete — great work!', true);
      });
    }

    function markCompleteUI(initial){
      if (!completeBtn) return;
      completeBtn.setAttribute('data-complete', 'true');
      completeBtn.textContent = initial ? 'Completed on this device' : 'Module marked complete ✓';
      completeBtn.classList.add('is-complete');
    }

    fetch(schemaUrl, { credentials: 'same-origin' })
      .then(function(response){
        if (!response.ok) throw new Error('Failed to load quiz.');
        return response.json();
      })
      .then(function(payload){
        state.questions = Array.isArray(payload.questions) ? payload.questions : [];
        if (!state.questions.length && questionStage){
          questionStage.textContent = 'Quiz questions are coming soon.';
          disableControls(true);
          return;
        }
        renderQuestion();
        if (payload.user_score){
          updateSidebar(payload.user_score.score, payload.user_score.total_questions, payload.user_score.updated_at);
        }
      })
      .catch(function(){
        if (questionStage) questionStage.textContent = 'Unable to load quiz at the moment.';
        disableControls(true);
      });

    function disableControls(force){
      if (prevBtn) prevBtn.disabled = true;
      if (nextBtn) nextBtn.disabled = true;
      if (submitBtn) submitBtn.disabled = submitBtn ? true : false;
      if (force && progressLabel) progressLabel.textContent = 'Quiz unavailable';
      if (force && progressFill) progressFill.style.setProperty('--progress-value', '0%');
    }

    function renderQuestion(){
      if (!questionStage || !state.questions.length){
        return;
      }
      if (!isUnlocked){
        questionStage.innerHTML = '<p class="quiz-hint-line">Hit “Start Quiz” to load your first question.</p>';
        if (prevBtn) prevBtn.disabled = true;
        if (nextBtn) nextBtn.disabled = true;
        if (submitBtn){
          submitBtn.disabled = true;
          submitBtn.setAttribute('aria-disabled', 'true');
        }
        return;
      }
      var total = state.questions.length;
      state.current = clamp(state.current, 0, total - 1);
      var question = state.questions[state.current];
      var answered = state.answers[question.id];

      if (progressLabel){
        progressLabel.textContent = 'Question ' + (state.current + 1) + ' of ' + total;
      }
      var stagePercent = total ? Math.round(((state.current + 1) / total) * 100) : 0;
      if (progressFill){
        progressFill.style.setProperty('--progress-value', stagePercent + '%');
      }

      questionStage.innerHTML = '';

      var title = document.createElement('h3');
      title.textContent = question.prompt || 'Untitled question';
      questionStage.appendChild(title);

      var list = document.createElement('ul');
      (question.choices || []).forEach(function(choice){
        var choiceId = String(choice.id);
        var label = document.createElement('label');
        label.className = 'quiz-choice';

        var input = document.createElement('input');
        input.type = 'radio';
        input.name = 'active_question';
        input.value = choiceId;

        if (String(answered) === choiceId){
          input.checked = true;
          label.classList.add('is-selected');
        }

        input.addEventListener('change', function(){
          state.answers[question.id] = choiceId;
          state.hasSubmitted = false;
          state.evaluation = {};
          renderQuestion();
          updateNavState();
        });

        label.appendChild(input);
        var span = document.createElement('span');
        span.textContent = choice.text || '';
        label.appendChild(span);
        list.appendChild(label);

        applySubmissionStyles(label, choice, question.id);
      });
      questionStage.appendChild(list);

      if (state.hasSubmitted){
        appendFeedback(question.id);
      }

      updateNavState();
      updateSubmitState();
    }

    function applySubmissionStyles(label, choice, questionId){
      if (!state.hasSubmitted) return;
      var evaluation = state.evaluation[questionId];
      if (!evaluation) return;
      var choiceId = String(choice.id);
      if (choiceId === evaluation.correctChoiceId){
        label.classList.add('is-correct');
      }
      if (String(state.answers[questionId]) === choiceId && !evaluation.isUserCorrect){
        label.classList.add('is-incorrect');
      }
      if (String(state.answers[questionId]) === choiceId){
        label.classList.add('is-selected');
      }
    }

    function appendFeedback(questionId){
      var evaluation = state.evaluation[questionId];
      if (!evaluation) return;
      var note = document.createElement('p');
      note.className = 'quiz-feedback-line';
      note.textContent = evaluation.isUserCorrect ? 'Nice! You nailed this one.' : ('Correct answer: ' + (evaluation.correctText || ''));
      if (evaluation.isUserCorrect){
        note.classList.add('is-correct');
      } else {
        note.classList.add('is-incorrect');
      }
      questionStage.appendChild(note);
    }

    function updateNavState(){
      var total = state.questions.length;
      if (!prevBtn || !nextBtn) return;
      prevBtn.disabled = state.current === 0;
      var answeredCurrent = !!state.answers[state.questions[state.current].id];
      var atEnd = state.current >= total - 1;
      nextBtn.disabled = atEnd || !answeredCurrent;
      nextBtn.textContent = atEnd ? 'End of Quiz' : 'Next Question';
    }

    function updateSubmitState(){
      if (!submitBtn) return;
      if (!state.questions.length){
        submitBtn.disabled = true;
        return;
      }
      var answeredCount = Object.keys(state.answers).length;
      var total = state.questions.length;
      var ready = answeredCount >= total;
      submitBtn.disabled = !ready;
      submitBtn.setAttribute('aria-disabled', ready ? 'false' : 'true');
    }

    if (prevBtn){
      prevBtn.addEventListener('click', function(){
        if (state.current === 0) return;
        state.current -= 1;
        renderQuestion();
      });
    }

    if (nextBtn){
      nextBtn.addEventListener('click', function(){
        var total = state.questions.length;
        if (state.current >= total - 1) return;
        if (!state.answers[state.questions[state.current].id]) return;
        state.current += 1;
        renderQuestion();
      });
    }

    if (submitBtn){
      submitBtn.addEventListener('click', function(){
        handleSubmit();
      });
    }

    if (retakeBtn){
      retakeBtn.addEventListener('click', function(){
        if (retakeBtn.disabled) return;
        state.current = 0;
        state.answers = {};
        state.evaluation = {};
        state.hasSubmitted = false;
        state.latestScore = null;
        retakeBtn.disabled = true;
        if (resultCard){
          resultCard.classList.remove('is-visible');
          resultCard.textContent = '';
        }
        renderQuestion();
      });
    }

    function handleSubmit(){
      if (!state.questions.length){
        showResult('Quiz is still loading.', false);
        return;
      }
      var answeredCount = Object.keys(state.answers).length;
      var total = state.questions.length;
      if (answeredCount < total){
        showResult('Answer every question before submitting.', false);
        return;
      }

      var answersPayload = [];
      var score = 0;
      var evaluation = {};

      state.questions.forEach(function(question){
        var selected = state.answers[question.id];
        var choices = Array.isArray(question.choices) ? question.choices : [];
        var correctChoice = choices.find(function(choice){
          return choice.is_correct === true || choice.correct === true;
        });
        var isCorrect = correctChoice && String(selected) === String(correctChoice.id);
        if (isCorrect) score += 1;
        evaluation[question.id] = {
          correctChoiceId: correctChoice ? String(correctChoice.id) : '',
          correctText: correctChoice ? correctChoice.text : '',
          isUserCorrect: !!isCorrect,
        };
        answersPayload.push({
          question_id: question.id,
          answer_id: selected,
        });
      });

      state.hasSubmitted = true;
      state.evaluation = evaluation;
      state.latestScore = { score: score, total: total };
      renderQuestion();
      var intro = canSubmit ? 'Saving your score…' : 'Log in to save this attempt. Review your results below.';
      showResultCard(score, total, intro);
      if (retakeBtn){
        retakeBtn.disabled = false;
      }

      if (canSubmit && submitUrl){
        submitResults(answersPayload, score, total);
      }
      launchConfetti();
    }

    function submitResults(answersPayload, score, total){
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
          answers: answersPayload,
          total: total,
          score: score,
        }),
      })
        .then(function(response){
          if (!response.ok){
            return response.json().catch(function(){ return {}; }).then(function(body){
              var err = body.error || 'Unable to save score.';
              throw new Error(err);
            });
          }
          return response.json();
        })
        .then(function(payload){
          var serverScore = typeof payload.score === 'number' ? payload.score : score;
          var serverTotal = typeof payload.total_questions === 'number' ? payload.total_questions : total;
          var message = payload.message || 'Score saved!';
          showResult(message + ' (' + serverScore + '/' + serverTotal + ')', true);
          updateSidebar(serverScore, serverTotal, payload.updated_at);
          launchConfetti();
        })
        .catch(function(err){
          showResult(err.message || 'Unable to save score right now.', false);
        });
    }

    function showResult(message, success){
      if (!resultCard) return;
      resultCard.classList.add('is-visible');
      resultCard.innerHTML = '<strong>' + (success ? 'Nice progress!' : 'Heads up') + '</strong><p>' + message + '</p>';
    }

    function showResultCard(score, total, intro){
      if (!resultCard) return;
      var percent = total ? Math.round((score / total) * 100) : 0;
      var body = '<strong>' + percent + '% · ' + score + '/' + total + ' correct</strong>';
      if (intro){
        body += '<p>' + intro + '</p>';
      }
      resultCard.classList.add('is-visible');
      resultCard.innerHTML = body;
    }

    function updateSidebar(score, total, updatedAt){
      var percent = 0;
      if (typeof score === 'number' && typeof total === 'number' && total){
        percent = Math.round((score / total) * 100);
      }
      var valueEl = document.getElementById('sidebarProgressValue');
      var metaEl = document.getElementById('sidebarProgressMeta');
      var fillEl = document.getElementById('sidebarProgressFill');
      var pillText = document.getElementById('quizStartBtn');

      if (valueEl) valueEl.textContent = percent + '%';
      if (fillEl) fillEl.style.setProperty('--progress-value', percent + '%');
      if (metaEl){
        var timeText = updatedAt ? 'Updated ' + formatTimestamp(updatedAt) : 'Latest attempt just now';
        metaEl.textContent = score + ' of ' + total + ' correct · ' + timeText;
      }
      if (pillText){
        pillText.textContent = 'Continue Quiz';
      }
    }

    function launchConfetti(){
      if (!confettiHost) return;
      confettiHost.innerHTML = '';
      var colors = ['#4a6cff', '#7f93ff', '#1db954', '#facc15'];
      for (var i = 0; i < 16; i++){
        var piece = document.createElement('span');
        piece.className = 'confetti-piece';
        var color = colors[i % colors.length];
        piece.style.background = color;
        piece.style.left = Math.random() * 100 + '%';
        piece.style.top = '0';
        piece.style.animationDelay = (Math.random() * 0.2) + 's';
        confettiHost.appendChild(piece);
        (function(p){
          setTimeout(function(){ if (p && p.parentNode){ p.parentNode.removeChild(p); } }, 1500);
        })(piece);
      }
    }
  });
})();
