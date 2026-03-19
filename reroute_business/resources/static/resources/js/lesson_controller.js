// Lesson flow with persisted progress and resume support
(function(){
  var root = document.getElementById('lessonRoot');
  if (!root) return;

  var schemaUrl = root.getAttribute('data-schema-url');
  var attemptUrl = root.getAttribute('data-attempt-url');
  var progressUrl = root.getAttribute('data-progress-url');
  var inlineYtId = root.getAttribute('data-yt-id');
  var quizContainer = document.getElementById('lessonQuizContainer');
  var submitBtn = document.getElementById('lessonQuizSubmit');
  var resultEl = document.getElementById('lessonQuizResult');
  var lessonVideo = document.getElementById('lessonVideo');
  var player = null;
  var progressTimer = null;
  var state = {
    schema: null,
    answers: {},
    lastAnsweredOrder: 0,
    lastVideoTime: 0,
  };

  function getCookie(name){
    var value = null;
    if (!document.cookie) return value;
    document.cookie.split(';').forEach(function(part){
      var item = part.trim();
      if (item.substring(0, name.length + 1) === (name + '=')){
        value = decodeURIComponent(item.substring(name.length + 1));
      }
    });
    return value;
  }

  function postJSON(url, body){
    var headers = { 'Content-Type': 'application/json' };
    var csrf = getCookie('csrftoken');
    if (csrf){
      headers['X-CSRFToken'] = csrf;
    }
    return fetch(url, {
      method: 'POST',
      headers: headers,
      credentials: 'same-origin',
      body: JSON.stringify(body || {}),
    }).then(function(response){
      if (!response.ok){
        throw new Error('Bad response');
      }
      return response.json();
    });
  }

  function getCurrentVideoTime(){
    try {
      if (player && typeof player.getCurrentTime === 'function'){
        return Number(player.getCurrentTime() || 0);
      }
      if (lessonVideo){
        return Number(lessonVideo.currentTime || 0);
      }
    } catch (err){}
    return 0;
  }

  function scheduleProgressSave(completed){
    if (!progressUrl) return;
    if (progressTimer){
      clearTimeout(progressTimer);
    }
    progressTimer = setTimeout(function(){
      saveProgress(!!completed).catch(function(){});
    }, 300);
  }

  function saveProgress(completed){
    if (!progressUrl) return Promise.resolve(null);
    state.lastVideoTime = getCurrentVideoTime();
    return postJSON(progressUrl, {
      last_video_time: state.lastVideoTime,
      last_answered_question_order: state.lastAnsweredOrder,
      completed: completed === true,
      raw_state: {
        answers: state.answers,
      },
    });
  }

  function restoreProgress(progress){
    if (!progress) return;
    state.lastVideoTime = Number(progress.last_video_time || 0);
    state.lastAnsweredOrder = Number(progress.last_answered_question_order || 0);
    if (progress.raw_state && progress.raw_state.answers){
      state.answers = progress.raw_state.answers;
    }
  }

  function restoreVideoPosition(){
    if (!state.lastVideoTime) return;
    if (lessonVideo){
      lessonVideo.currentTime = state.lastVideoTime;
      return;
    }
    if (player && typeof player.seekTo === 'function'){
      player.seekTo(state.lastVideoTime, true);
    }
  }

  function bindVideoTracking(){
    if (lessonVideo){
      lessonVideo.addEventListener('timeupdate', function(){
        state.lastVideoTime = Number(lessonVideo.currentTime || 0);
      });
      lessonVideo.addEventListener('pause', function(){ scheduleProgressSave(false); });
      lessonVideo.addEventListener('ended', function(){ saveProgress(true).catch(function(){}); });
    }
    setInterval(function(){
      saveProgress(false).catch(function(){});
    }, 15000);
  }

  function loadYouTubeAPI(cb){
    if (window.YT && window.YT.Player){
      cb();
      return;
    }
    var tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    var firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
    var prior = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = function(){
      if (typeof prior === 'function'){
        try { prior(); } catch (err){}
      }
      cb();
    };
  }

  function bootYouTube(videoId){
    if (!videoId) return;
    loadYouTubeAPI(function(){
      player = new YT.Player('ytPlayer', {
        videoId: videoId,
        playerVars: { playsinline: 1, rel: 0, modestbranding: 1, origin: window.location.origin },
        events: {
          onReady: function(){
            restoreVideoPosition();
          },
          onStateChange: function(event){
            try {
              if (event.data === YT.PlayerState.ENDED){
                saveProgress(true).catch(function(){});
              }
            } catch (err){}
          },
        },
      });
    });
  }

  function setSavedAnswer(qid, payload){
    state.answers[String(qid)] = payload;
  }

  function getSavedAnswer(qid){
    return state.answers[String(qid)] || null;
  }

  function renderQuiz(){
    if (!quizContainer || !state.schema) return;
    quizContainer.innerHTML = '';

    (state.schema.questions || []).forEach(function(question){
      var box = document.createElement('div');
      box.className = 'lesson-quiz-question';

      var heading = document.createElement('h3');
      heading.textContent = question.prompt || '';
      box.appendChild(heading);

      var saved = getSavedAnswer(question.id);
      if (question.qtype === 'MULTIPLE_CHOICE'){
        var list = document.createElement('div');
        list.className = 'lesson-quiz-choices';
        (question.choices || []).forEach(function(choice){
          var id = 'q' + question.id + '_' + choice.id;
          var label = document.createElement('label');
          label.setAttribute('for', id);
          var input = document.createElement('input');
          input.type = 'radio';
          input.name = 'q_' + question.id;
          input.id = id;
          input.value = choice.id;
          if (saved && String(saved.selected_choice_id) === String(choice.id)){
            input.checked = true;
          }
          input.addEventListener('change', function(){
            setSavedAnswer(question.id, { selected_choice_id: choice.id });
            state.lastAnsweredOrder = Math.max(state.lastAnsweredOrder, Number(question.order || 0));
            scheduleProgressSave(false);
          });
          label.appendChild(input);
          var text = document.createElement('span');
          text.textContent = (choice.label || '').toUpperCase() + ') ' + (choice.text || '');
          label.appendChild(text);
          list.appendChild(label);
        });
        box.appendChild(list);
      } else {
        var textarea = document.createElement('textarea');
        textarea.rows = 3;
        textarea.name = 't_' + question.id;
        textarea.placeholder = 'Type your answer...';
        textarea.classList.add('rr-w-100');
        if (saved && saved.open_text){
          textarea.value = saved.open_text;
        }
        textarea.addEventListener('input', function(){
          setSavedAnswer(question.id, { open_text: textarea.value });
          state.lastAnsweredOrder = Math.max(state.lastAnsweredOrder, Number(question.order || 0));
          scheduleProgressSave(false);
        });
        box.appendChild(textarea);
      }

      quizContainer.appendChild(box);
    });
  }

  function submitQuiz(){
    if (!state.schema) return;
    var tasks = [];
    var scoredTotal = 0;
    var correctCount = 0;
    var feedbackItems = [];

    (state.schema.questions || []).forEach(function(question){
      if (question.qtype === 'MULTIPLE_CHOICE'){
        var selected = document.querySelector('input[name="q_' + question.id + '"]:checked');
        if (!selected) return;
        setSavedAnswer(question.id, { selected_choice_id: selected.value });
        if (question.is_scored) scoredTotal += 1;
        tasks.push(
          postJSON(attemptUrl, {
            question_id: question.id,
            selected_choice_id: selected.value,
            current_time: getCurrentVideoTime(),
          }).then(function(response){
            state.lastAnsweredOrder = Math.max(state.lastAnsweredOrder, Number(question.order || 0));
            if (question.is_scored && response && response.is_correct){
              correctCount += 1;
            }
            feedbackItems.push({
              prompt: question.prompt,
              explanation: response && response.explanation ? response.explanation : '',
              isCorrect: !!(response && response.is_correct),
            });
          }).catch(function(){})
        );
      } else {
        var textarea = document.querySelector('textarea[name="t_' + question.id + '"]');
        var text = textarea ? textarea.value.trim() : '';
        if (!text) return;
        setSavedAnswer(question.id, { open_text: text });
        tasks.push(
          postJSON(attemptUrl, {
            question_id: question.id,
            open_text: text,
            current_time: getCurrentVideoTime(),
          }).then(function(){
            state.lastAnsweredOrder = Math.max(state.lastAnsweredOrder, Number(question.order || 0));
            feedbackItems.push({
              prompt: question.prompt,
              explanation: question.explanation || '',
              isCorrect: null,
            });
          }).catch(function(){})
        );
      }
    });

    Promise.all(tasks).then(function(){
      if (resultEl){
        var summary = 'You answered ' + correctCount + ' of ' + scoredTotal + ' correctly.';
        if (feedbackItems.length){
          summary += '\n\n' + feedbackItems.map(function(item){
            if (item.explanation){
              if (item.isCorrect === null){
                return item.prompt + ': ' + item.explanation;
              }
              return item.prompt + ': ' + (item.isCorrect ? 'Correct. ' : 'Review this. ') + item.explanation;
            }
            return item.prompt;
          }).join('\n');
        }
        resultEl.textContent = summary;
      }
      saveProgress(false).catch(function(){});
    });
  }

  if (submitBtn){
    submitBtn.addEventListener('click', submitQuiz);
  }

  window.addEventListener('beforeunload', function(){
    if (progressTimer){
      clearTimeout(progressTimer);
    }
    saveProgress(false).catch(function(){});
  });

  fetch(schemaUrl, { credentials: 'same-origin' })
    .then(function(response){ return response.json(); })
    .then(function(data){
      state.schema = data || {};
      restoreProgress(state.schema.progress);
      renderQuiz();
      bindVideoTracking();
      if (state.schema.lesson && state.schema.lesson.youtube_video_id){
        bootYouTube(state.schema.lesson.youtube_video_id || inlineYtId);
      } else {
        restoreVideoPosition();
      }
    })
    .catch(function(){});
})();
