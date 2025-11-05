// Interactive lesson controller for Resume Basics 101 and similar lessons
(function(){
  const $ = (sel) => document.querySelector(sel);

  const overlay = $('#lessonOverlay');
  const dialog = $('#lessonDialog');
  const promptEl = $('#lessonPrompt');
  const choicesEl = $('#lessonChoices');
  const openWrap = $('#lessonOpenEnded');
  const openArea = $('#lessonTextarea');
  const openSubmit = $('#lessonSubmitOpen');
  const feedbackEl = $('#lessonFeedback');
  const completeOverlay = $('#lessonCompleteOverlay');
  const completeDialog = $('#lessonComplete');
  const completeSummary = $('#lessonCompleteSummary');
  const completeClose = $('#lessonCompleteClose');

  const endpoints = window.__LESSON_ENDPOINTS__;
  const slug = window.__LESSON_SLUG__;
  const csrfToken = getCookie('csrftoken');

  let schema = null;
  let player = null;
  let useYouTube = false;
  let ytReady = false;
  let ytPoll = null;
  let lastTime = 0;
  let videoEnded = false;

  let state = {
    answered: {}, // questionId -> {completed: bool, correct: bool, attempts: n}
    orderDone: 0,
    currentIndex: 0,
  };

  const storageKey = `resources:lesson:${slug}:state`;
  try { const saved = sessionStorage.getItem(storageKey); if (saved) state = Object.assign(state, JSON.parse(saved)); } catch(e) {}

  fetch(endpoints.schema, { credentials: 'same-origin' })
    .then(r => r.json())
    .then(data => {
      schema = data;
      useYouTube = !!(data && data.lesson && data.lesson.youtube_video_id);
      if (useYouTube) {
        bootYouTube(data.lesson.youtube_video_id);
      } else {
        bootHTML5();
      }
      // hydrate from server progress
      if (data.progress) {
        state.orderDone = data.progress.last_answered_question_order || 0;
        const t = data.progress.last_video_time || 0;
        if (!useYouTube) {
          try { const v = $('#lessonVideo'); if (v && t) v.currentTime = t; } catch(e) {}
        } // for YouTube, we seek after the player is ready
      }
    })
    .catch(err => console.error('Failed to load lesson schema', err));

  function bootHTML5(){
    const video = $('#lessonVideo');
    if (!video) return;
    player = {
      get time(){ return video.currentTime; },
      set time(t){ video.currentTime = t; },
      play(){ try { return video.play(); } catch(e) { return Promise.resolve(); } },
      pause(){ try { video.pause(); } catch(e) {} },
      onTime(cb){ video.addEventListener('timeupdate', () => cb(video.currentTime)); },
      onSeekAttempt(cb){ video.addEventListener('seeking', () => cb(video.currentTime)); },
    };
    // Track when the video ends to gate completion
    try { video.addEventListener('ended', onVideoEnded); } catch(e){}
    bindCommon();
  }

  function bootYouTube(videoId){
    const YT_ID = videoId || window.__LESSON_YT_ID__;
    if (!YT_ID) return;
    loadYouTubeAPI(() => {
      ytReady = true;
      // eslint-disable-next-line no-undef
      player = new YT.Player('ytPlayer', {
        videoId: YT_ID,
        playerVars: {
          playsinline: 1,
          rel: 0,
          modestbranding: 1,
          origin: window.location.origin,
        },
        events: {
          onReady: () => {
            const t = (schema && schema.progress && schema.progress.last_video_time) || 0;
            if (t) try { player.seekTo(t, true); } catch(e) {}
            bindYT();
          },
          onStateChange: (ev) => {
            // 1 = PLAYING, 2 = PAUSED
            if (ev.data === 1) startYTPoll();
            else stopYTPoll();
            try {
              if (typeof YT !== 'undefined' && ev.data === YT.PlayerState.ENDED) {
                onVideoEnded();
              }
            } catch(e){}
          },
        }
      });
    });
  }

  function bindYT(){
    bindCommon();
  }

  function bindCommon(){
    if (openSubmit) openSubmit.addEventListener('click', submitOpenEnded);
    if (completeClose) completeClose.addEventListener('click', closeCompletion);
    if (completeOverlay) completeOverlay.addEventListener('click', closeCompletion);
    document.addEventListener('keydown', (e)=>{ if (!completeDialog.hidden && (e.key === 'Escape' || e.key === 'Esc')) closeCompletion(); });
    if (!useYouTube) {
      const video = $('#lessonVideo');
      player.onTime(onAnyTimeUpdate);
      player.onSeekAttempt(onAnySeekAttempt);
    } else {
      startYTPoll();
    }
  }

  function startYTPoll(){
    stopYTPoll();
    ytPoll = setInterval(() => {
      if (!player || typeof player.getCurrentTime !== 'function') return;
      const t = player.getCurrentTime();
      onAnyTimeUpdate(t);
      // detect forward seeking beyond next checkpoint
      const nextQ = nextUnansweredQuestion();
      if (nextQ && t > nextQ.timestamp_seconds - 0.2 && t > lastTime + 0.7) {
        try { player.seekTo(Math.max(0, nextQ.timestamp_seconds - 0.5), true); } catch(e) {}
      }
      lastTime = t;
    }, 250);
  }
  function stopYTPoll(){ if (ytPoll) { clearInterval(ytPoll); ytPoll = null; } }

  function onAnyTimeUpdate(current){
    persistProgress(false);
    const nextQ = nextUnansweredQuestion();
    if (!nextQ) return; // all done
    const t = typeof current === 'number' ? current : (player ? player.time : 0);
    if (t >= nextQ.timestamp_seconds - 0.1) {
      pausePlayer();
      showQuestion(nextQ);
    }
  }

  function onAnySeekAttempt(target){
    const nextQ = nextUnansweredQuestion();
    if (!nextQ) return;
    const t = typeof target === 'number' ? target : (player ? player.time : 0);
    if (t > nextQ.timestamp_seconds - 0.2) {
      seekTo(Math.max(0, nextQ.timestamp_seconds - 0.5));
    }
  }

  function nextUnansweredQuestion(){
    const qs = (schema && schema.questions) ? schema.questions : [];
    for (let i=0;i<qs.length;i++){
      const q = qs[i];
      const st = state.answered[q.id];
      if (!st || !st.completed) return q;
    }
    return null;
  }

  function showQuestion(q){
    promptEl.textContent = q.prompt;
    feedbackEl.textContent = '';
    feedbackEl.className = 'lesson-feedback';
    choicesEl.innerHTML = '';

    if (q.qtype === 'MULTIPLE_CHOICE') {
      openWrap.hidden = true;
      choicesEl.hidden = false;
      (q.choices || []).forEach(ch => {
        const btn = document.createElement('button');
        btn.className = 'lesson-btn lesson-choice-btn';
        btn.textContent = `${(ch.label || '').toUpperCase()}) ${ch.text}`;
        btn.addEventListener('click', () => submitChoice(q, ch));
        choicesEl.appendChild(btn);
      });
    } else {
      choicesEl.hidden = true;
      openWrap.hidden = false;
      setTimeout(()=>openArea && openArea.focus(), 50);
    }

    overlay.hidden = false; overlay.setAttribute('aria-hidden','false');
    dialog.hidden = false; dialog.setAttribute('aria-hidden','false');
  }

  function submitChoice(q, ch){
    const body = {
      question_id: q.id,
      selected_choice_id: ch.id,
      current_time: currentTime(),
    };
    postJSON(endpoints.attempt, body).then(res => {
      const ok = !!res && typeof res.is_correct === 'boolean' ? res.is_correct : false;
      const qst = state.answered[q.id] || { attempts: 0 };
      qst.attempts = (qst.attempts||0) + 1;
      qst.correct = ok;
      qst.completed = ok; // require correct to continue
      state.answered[q.id] = qst;
      if (ok) {
        showFeedback('Correct!', true);
        state.orderDone = Math.max(state.orderDone, q.order);
        setTimeout(()=>{ hideDialog(); resumeSlightly(); persistProgress(true); }, 550);
      } else {
        showFeedback('Try Again', false);
        persistProgress(false);
      }
    }).catch(()=>{
      showFeedback('Network error — try again', false);
    });
  }

  function submitOpenEnded(){
    const q = nextUnansweredQuestion();
    if (!q) return;
    const text = (openArea.value || '').trim();
    if (!text) { openArea.focus(); return; }
    const body = {
      question_id: q.id,
      open_text: text,
      current_time: currentTime(),
    };
    postJSON(endpoints.attempt, body).then(() => {
      const qst = state.answered[q.id] || { attempts: 0 };
      qst.attempts = (qst.attempts||0) + 1;
      qst.correct = false; // not scored
      qst.completed = true; // completion on submit
      state.answered[q.id] = qst;
      showFeedback('Saved', true);
      state.orderDone = Math.max(state.orderDone, q.order);
      setTimeout(()=>{ hideDialog(); resumeSlightly(); persistProgress(true); }, 550);
    }).catch(()=>{
      showFeedback('Network error — try again', false);
    });
  }

  function showFeedback(msg, success){
    feedbackEl.textContent = msg;
    feedbackEl.className = 'lesson-feedback ' + (success ? 'success' : 'error');
  }

  function hideDialog(){
    dialog.hidden = true; dialog.setAttribute('aria-hidden','true');
    overlay.hidden = true; overlay.setAttribute('aria-hidden','true');
    feedbackEl.textContent = '';
  }

  function resumeSlightly(){
    seekTo(currentTime() + 0.2);
    const nextQ = nextUnansweredQuestion();
    if (!nextQ) {
      // All questions answered; only show completion after video ends
      if (videoEnded) {
        showCompletion();
      } else {
        playPlayer();
      }
    } else {
      playPlayer();
    }
  }

  function allQuestionsAnswered(){
    const qs = (schema && schema.questions) ? schema.questions : [];
    if (!qs.length) return false;
    for (let i=0;i<qs.length;i++){
      const q = qs[i];
      const st = state.answered[q.id];
      if (!st || !st.completed) return false;
    }
    return true;
  }

  function onVideoEnded(){
    videoEnded = true;
    // If all questions are answered, now show completion
    if (allQuestionsAnswered()) {
      showCompletion();
    } else {
      // Persist final time/state without marking completed
      persistProgress(true);
    }
  }

  function showCompletion(){
    const correct = (schema && schema.lesson && schema.progress) ? (schema.progress.correct_count) : 0;
    let localCorrect = 0; const scoredCount = (schema.questions||[]).filter(q => q.is_scored).length;
    (schema.questions||[]).forEach(q => { if (q.is_scored && state.answered[q.id] && state.answered[q.id].completed && state.answered[q.id].correct) localCorrect++; });
    const correctCount = Number.isFinite(correct) && correct >= localCorrect ? correct : localCorrect;
    completeSummary.textContent = `Lesson Complete – Great work! You answered ${correctCount} of ${scoredCount} correctly.`;

    completeOverlay.hidden = false; completeOverlay.setAttribute('aria-hidden','false');
    completeDialog.hidden = false; completeDialog.setAttribute('aria-hidden','false');
    postJSON(endpoints.progress, {
      last_video_time: currentTime(),
      last_answered_question_order: state.orderDone,
      completed: true,
      raw_state: state,
    }).catch(()=>{});
  }

  function closeCompletion(){
    completeDialog.hidden = true; completeDialog.setAttribute('aria-hidden','true');
    completeOverlay.hidden = true; completeOverlay.setAttribute('aria-hidden','true');
  }

  function persistProgress(flush){
    try { sessionStorage.setItem(storageKey, JSON.stringify(state)); } catch(e) {}
    if (flush) {
      const answeredCount = Object.keys(state.answered||{}).length;
      const started = answeredCount > 0;
      const completedNow = started && allQuestionsAnswered() && videoEnded;
      postJSON(endpoints.progress, {
        last_video_time: currentTime(),
        last_answered_question_order: state.orderDone,
        raw_state: state,
        completed: completedNow,
      }).catch(()=>{});
    }
  }

  function currentTime(){
    try {
      if (useYouTube && player && typeof player.getCurrentTime === 'function') return player.getCurrentTime();
      const v = $('#lessonVideo');
      return v ? v.currentTime : 0;
    } catch(e) { return 0; }
  }
  function pausePlayer(){ try { useYouTube ? player.pauseVideo() : $('#lessonVideo').pause(); } catch(e) {} }
  function playPlayer(){ try { useYouTube ? player.playVideo() : $('#lessonVideo').play(); } catch(e) {} }
  function seekTo(t){ try { useYouTube ? player.seekTo(Math.max(0, t), true) : ($('#lessonVideo').currentTime = Math.max(0, t)); } catch(e) {} }

  function postJSON(url, body){
    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      credentials: 'same-origin',
      body: JSON.stringify(body || {}),
    }).then(r => {
      if (!r.ok) throw new Error('Bad response');
      return r.json();
    });
  }

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function loadYouTubeAPI(cb){
    if (window.YT && window.YT.Player) { cb(); return; }
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
    const prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = function(){
      if (typeof prev === 'function') try { prev(); } catch(e) {}
      cb();
    };
  }
})();
