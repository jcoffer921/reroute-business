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
    var progressUrl = quizRoot.getAttribute('data-progress-url');
    var canSubmit = quizRoot.getAttribute('data-can-submit') === 'true';

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
      completion: null,
    };
    var isUnlocked = false;
    var persistTimer = null;

    function getQuestionType(question){
      return question.qtype || 'mc';
    }

    function getAnswerRecord(questionId){
      return state.answers[questionId] || null;
    }

    function setAnswerValue(questionId, qtype, value){
      state.answers[questionId] = { value: value, qtype: qtype };
      queueProgressSave(false);
    }

    function hasAnswer(questionId, qtype){
      var record = getAnswerRecord(questionId);
      if (!record) return false;
      if (qtype === 'open'){
        return !!record.value && record.value.trim().length > 0;
      }
      return record.value !== null && record.value !== undefined && record.value !== '';
    }

    function markCompleteUI(initial){
      if (!completeBtn) return;
      completeBtn.setAttribute('data-complete', 'true');
      completeBtn.textContent = initial ? 'Completed' : 'Module marked complete';
      completeBtn.classList.add('is-complete');
    }

    function resetCompleteUI(){
      if (!completeBtn) return;
      completeBtn.removeAttribute('data-complete');
      completeBtn.textContent = 'Mark Module Complete';
      completeBtn.classList.remove('is-complete');
    }

    function normalizeEvaluation(raw){
      var normalized = {};
      if (!raw) return normalized;
      Object.keys(raw).forEach(function(key){
        var item = raw[key] || {};
        var questionId = String(item.question_id || key);
        normalized[questionId] = {
          correctChoiceId: String(item.correct_choice_id || ''),
          correctText: item.correct_text || '',
          explanation: item.explanation || '',
          isUserCorrect: item.is_user_correct === true,
          questionType: item.question_type || '',
          saved: item.saved === true,
        };
      });
      return normalized;
    }

    function buildRawState(){
      return {
        current: state.current,
        answers: state.answers,
        has_submitted: state.hasSubmitted,
        evaluation: state.evaluation,
      };
    }

    function restoreProgress(progress){
      if (!progress) return;
      state.completion = progress;
      if (typeof progress.last_question_order === 'number' && progress.last_question_order > 0){
        state.current = clamp(progress.last_question_order - 1, 0, Math.max(state.questions.length - 1, 0));
      }
      if (progress.raw_state && progress.raw_state.answers){
        state.answers = progress.raw_state.answers;
      }
      if (progress.raw_state && progress.raw_state.has_submitted){
        state.hasSubmitted = true;
      }
      if (progress.raw_state && progress.raw_state.evaluation){
        state.evaluation = normalizeEvaluation(progress.raw_state.evaluation);
      }
      if (progress.completed_at){
        markCompleteUI(true);
      }
    }

    function getCompletionPercent(){
      if (!state.questions.length) return 0;
      if (state.completion && state.completion.completed_at) return 100;
      return Math.round(((state.current + 1) / state.questions.length) * 100);
    }

    function updateSidebar(score, total, updatedAt){
      var valueEl = document.getElementById('sidebarProgressValue');
      var metaEl = document.getElementById('sidebarProgressMeta');
      var fillEl = document.getElementById('sidebarProgressFill');
      var pillText = document.getElementById('quizStartBtn');
      var percent = getCompletionPercent();

      if (typeof score === 'number' && typeof total === 'number'){
        state.latestScore = { score: score, total: total };
      }

      if (valueEl) valueEl.textContent = percent + '%';
      if (fillEl) fillEl.style.setProperty('--progress-value', percent + '%');
      if (metaEl){
        var timeText = updatedAt ? 'Updated ' + formatTimestamp(updatedAt) : 'Progress saved just now';
        if (state.latestScore && state.latestScore.total){
          var accuracy = Math.round((state.latestScore.score / state.latestScore.total) * 100);
          metaEl.textContent = accuracy + '% quiz accuracy · ' + timeText;
        } else if (state.completion && state.completion.completed_at){
          metaEl.textContent = 'Completed · ' + timeText;
        } else {
          metaEl.textContent = 'In progress · ' + timeText;
        }
      }
      if (pillText) pillText.textContent = 'Continue Quiz';
    }

    function persistProgress(completed, silent){
      if (!progressUrl) return Promise.resolve(null);
      var csrf = getCookie('csrftoken');
      var headers = { 'Content-Type': 'application/json' };
      if (csrf){
        headers['X-CSRFToken'] = csrf;
      }
      return fetch(progressUrl, {
        method: 'POST',
        headers: headers,
        credentials: 'same-origin',
        body: JSON.stringify({
          last_question_order: state.questions.length ? (state.current + 1) : 0,
          score_percent: state.latestScore && state.latestScore.total ? Math.round((state.latestScore.score / state.latestScore.total) * 100) : 0,
          completed: completed === true,
          raw_state: buildRawState(),
        }),
      })
        .then(function(response){
          if (!response.ok){
            throw new Error('Unable to save progress.');
          }
          return response.json();
        })
        .then(function(payload){
          state.completion = payload.progress || state.completion;
          if (completed === true){
            markCompleteUI(false);
          }
          updateSidebar(
            state.latestScore ? state.latestScore.score : null,
            state.latestScore ? state.latestScore.total : null,
            state.completion ? state.completion.updated_at : null
          );
          return payload;
        })
        .catch(function(err){
          if (!silent){
            throw err;
          }
          return null;
        });
    }

    function queueProgressSave(completed){
      if (!progressUrl) return;
      if (persistTimer){
        clearTimeout(persistTimer);
      }
      persistTimer = setTimeout(function(){
        persistProgress(!!completed, true).catch(function(){});
      }, 250);
    }

    function unlockQuiz(){
      if (isUnlocked) return;
      isUnlocked = true;
      quizRoot.classList.remove('quiz-flow--locked');
      quizRoot.setAttribute('data-state', 'active');
      if (lockScreen){
        lockScreen.style.display = 'none';
      }
      queueProgressSave(false);
      renderQuestion();
    }

    function handleStartClick(){
      unlockQuiz();
      if (quizSection){
        quizSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }

    function disableControls(force){
      if (prevBtn) prevBtn.disabled = true;
      if (nextBtn) nextBtn.disabled = true;
      if (submitBtn) submitBtn.disabled = true;
      if (force && progressLabel) progressLabel.textContent = 'Quiz unavailable';
      if (force && progressFill) progressFill.style.setProperty('--progress-value', '0%');
    }

    function applySubmissionStyles(label, choice, questionId){
      if (!state.hasSubmitted) return;
      var evaluation = state.evaluation[questionId];
      if (!evaluation) return;
      var choiceId = String(choice.id);
      if (choiceId === evaluation.correctChoiceId){
        label.classList.add('is-correct');
      }
      var record = getAnswerRecord(questionId);
      var answerValue = record ? record.value : null;
      if (String(answerValue) === choiceId && !evaluation.isUserCorrect){
        label.classList.add('is-incorrect');
      }
      if (String(answerValue) === choiceId){
        label.classList.add('is-selected');
      }
    }

    function appendFeedback(question){
      var qtype = getQuestionType(question);
      var evaluation = state.evaluation[String(question.id)];
      if (!evaluation) return;

      var note = document.createElement('p');
      note.className = 'quiz-feedback-line';
      if (qtype === 'open'){
        note.textContent = evaluation.saved ? 'Response saved for review.' : 'No response saved for this question.';
      } else {
        note.textContent = evaluation.isUserCorrect ? 'Nice! You nailed this one.' : ('Correct answer: ' + (evaluation.correctText || ''));
        note.classList.add(evaluation.isUserCorrect ? 'is-correct' : 'is-incorrect');
      }
      questionStage.appendChild(note);
      if (evaluation.explanation){
        var explainer = document.createElement('p');
        explainer.className = 'quiz-feedback-explainer';
        explainer.textContent = evaluation.explanation;
        questionStage.appendChild(explainer);
      }
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
      var qtype = getQuestionType(question);
      var answerRecord = getAnswerRecord(question.id) || {};
      var answeredValue = answerRecord.value;

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

      if (qtype === 'open'){
        var openWrap = document.createElement('div');
        openWrap.className = 'quiz-open-wrap';
        var textArea = document.createElement('textarea');
        textArea.className = 'quiz-open-input';
        textArea.placeholder = 'Type your response...';
        textArea.value = answeredValue || '';
        textArea.addEventListener('input', function(){
          state.hasSubmitted = false;
          state.evaluation = {};
          setAnswerValue(question.id, qtype, textArea.value);
          updateNavState();
          updateSubmitState();
        });
        openWrap.appendChild(textArea);
        questionStage.appendChild(openWrap);
      } else {
        var list = document.createElement('ul');
        (question.choices || []).forEach(function(choice){
          var choiceId = String(choice.id);
          var label = document.createElement('label');
          label.className = 'quiz-choice';

          var input = document.createElement('input');
          input.type = 'radio';
          input.name = 'active_question';
          input.value = choiceId;

          if (String(answeredValue) === choiceId){
            input.checked = true;
            label.classList.add('is-selected');
          }

          input.addEventListener('change', function(){
            state.hasSubmitted = false;
            state.evaluation = {};
            setAnswerValue(question.id, qtype, choiceId);
            renderQuestion();
            updateNavState();
            updateSubmitState();
          });

          label.appendChild(input);
          var span = document.createElement('span');
          span.textContent = choice.text || '';
          label.appendChild(span);
          list.appendChild(label);

          applySubmissionStyles(label, choice, String(question.id));
        });
        questionStage.appendChild(list);
      }

      if (state.hasSubmitted){
        appendFeedback(question);
      }

      updateNavState();
      updateSubmitState();
    }

    function updateNavState(){
      if (!prevBtn || !nextBtn) return;
      var total = state.questions.length;
      prevBtn.disabled = state.current === 0;
      var currentQuestion = state.questions[state.current];
      var answeredCurrent = hasAnswer(currentQuestion.id, getQuestionType(currentQuestion));
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
      var ready = state.questions.every(function(question){
        return hasAnswer(question.id, getQuestionType(question));
      });
      submitBtn.disabled = !ready;
      submitBtn.setAttribute('aria-disabled', ready ? 'false' : 'true');
    }

    function showResult(message, success){
      if (!resultCard) return;
      resultCard.classList.add('is-visible');
      resultCard.innerHTML = '<strong>' + (success ? 'Nice progress!' : 'Heads up') + '</strong><p>' + message + '</p>';
    }

    function showResultCard(score, total, intro){
      if (!resultCard) return;
      var body = '';
      if (typeof score === 'number'){
        var percent = total ? Math.round((score / total) * 100) : 0;
        body = '<strong>' + percent + '% · ' + score + '/' + total + ' correct</strong>';
      } else {
        body = '<strong>Checking your answers…</strong>';
      }
      if (intro){
        body += '<p>' + intro + '</p>';
      }
      resultCard.classList.add('is-visible');
      resultCard.innerHTML = body;
    }

    function launchConfetti(){
      if (!confettiHost) return;
      confettiHost.innerHTML = '';
      var colors = ['#4a6cff', '#7f93ff', '#1db954', '#facc15'];
      for (var i = 0; i < 16; i++){
        var piece = document.createElement('span');
        piece.className = 'confetti-piece';
        piece.style.background = colors[i % colors.length];
        piece.style.left = Math.random() * 100 + '%';
        piece.style.top = '0';
        piece.style.animationDelay = (Math.random() * 0.2) + 's';
        confettiHost.appendChild(piece);
        (function(p){
          setTimeout(function(){
            if (p && p.parentNode){
              p.parentNode.removeChild(p);
            }
          }, 1500);
        })(piece);
      }
    }

    function handleSubmit(){
      if (!state.questions.length){
        showResult('Quiz is still loading.', false);
        return;
      }

      var answeredCount = 0;
      var total = state.questions.length;
      var answersPayload = [];

      state.questions.forEach(function(question){
        var qtype = getQuestionType(question);
        var record = getAnswerRecord(question.id);
        var value = record ? record.value : '';
        if (typeof value === 'string'){
          value = value.trim();
        }
        if (value){
          answeredCount += 1;
        }

        if (qtype === 'open'){
          answersPayload.push({
            question_id: question.id,
            text_answer: value || '',
          });
        } else {
          answersPayload.push({
            question_id: question.id,
            answer_id: value,
          });
        }
      });

      if (answeredCount < total){
        showResult('Answer every question before submitting.', false);
        return;
      }

      if (!canSubmit || !submitUrl){
        showResult('Log in to save this attempt. Your preview answers are not scored server-side.', false);
        return;
      }

      showResultCard(null, total, 'Saving your score…');
      submitResults(answersPayload, total);
    }

    function submitResults(answersPayload, total){
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
        }),
      })
        .then(function(response){
          if (!response.ok){
            return response.json().catch(function(){ return {}; }).then(function(body){
              throw new Error(body.error || 'Unable to save score.');
            });
          }
          return response.json();
        })
        .then(function(payload){
          var serverScore = typeof payload.score === 'number' ? payload.score : 0;
          var serverTotal = typeof payload.total_questions === 'number' ? payload.total_questions : total;
          state.hasSubmitted = true;
          state.evaluation = normalizeEvaluation(payload.evaluation);
          state.latestScore = { score: serverScore, total: serverTotal };
          state.completion = payload.progress || state.completion;
          renderQuestion();
          showResultCard(serverScore, serverTotal, payload.message || 'Score saved.');
          updateSidebar(serverScore, serverTotal, payload.updated_at);
          if (retakeBtn){
            retakeBtn.disabled = false;
          }
          launchConfetti();
        })
        .catch(function(err){
          showResult(err.message || 'Unable to save score right now.', false);
        });
    }

    if (startBtn){
      startBtn.addEventListener('click', handleStartClick);
    }
    if (inlineStartBtn){
      inlineStartBtn.addEventListener('click', handleStartClick);
    }
    if (prevBtn){
      prevBtn.addEventListener('click', function(){
        if (state.current === 0) return;
        state.current -= 1;
        queueProgressSave(false);
        renderQuestion();
      });
    }
    if (nextBtn){
      nextBtn.addEventListener('click', function(){
        var total = state.questions.length;
        if (state.current >= total - 1) return;
        var currentQuestion = state.questions[state.current];
        if (!hasAnswer(currentQuestion.id, getQuestionType(currentQuestion))) return;
        state.current += 1;
        queueProgressSave(false);
        renderQuestion();
      });
    }
    if (submitBtn){
      submitBtn.addEventListener('click', handleSubmit);
    }
    if (retakeBtn){
      retakeBtn.addEventListener('click', function(){
        if (retakeBtn.disabled) return;
        state.current = 0;
        state.answers = {};
        state.evaluation = {};
        state.hasSubmitted = false;
        state.latestScore = null;
        state.completion = null;
        retakeBtn.disabled = true;
        resetCompleteUI();
        if (resultCard){
          resultCard.classList.remove('is-visible');
          resultCard.textContent = '';
        }
        queueProgressSave(false);
        renderQuestion();
        updateSidebar(null, null, null);
      });
    }
    if (completeBtn){
      completeBtn.addEventListener('click', function(){
        if (completeBtn.getAttribute('data-complete') === 'true') return;
        persistProgress(true, false)
          .then(function(){
            showResult('Module marked complete. Your progress is now saved on the server.', true);
          })
          .catch(function(){
            showResult('Unable to save completion right now.', false);
          });
      });
    }

    window.addEventListener('beforeunload', function(){
      if (persistTimer){
        clearTimeout(persistTimer);
      }
      persistProgress(false, true);
    });

    fetch(schemaUrl, { credentials: 'same-origin' })
      .then(function(response){
        if (!response.ok) throw new Error('Failed to load quiz.');
        return response.json();
      })
      .then(function(payload){
        state.questions = Array.isArray(payload.questions) ? payload.questions : [];
        if (!state.questions.length){
          if (questionStage) questionStage.textContent = 'Quiz questions are coming soon.';
          disableControls(true);
          return;
        }
        restoreProgress(payload.progress);
        if (payload.user_score){
          state.latestScore = {
            score: payload.user_score.score,
            total: payload.user_score.total_questions,
          };
          updateSidebar(payload.user_score.score, payload.user_score.total_questions, payload.user_score.updated_at);
        } else if (payload.progress){
          updateSidebar(null, null, payload.progress.updated_at);
        }
        renderQuestion();
      })
      .catch(function(){
        if (questionStage) questionStage.textContent = 'Unable to load quiz at the moment.';
        disableControls(true);
      });
  });
})();
