// Interactive lesson controller for Resume Basics 101 and similar lessons
(function(){
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  const video = $('#lessonVideo');
  if (!video) return;

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
  let state = {
    answered: {}, // questionId -> {completed: bool, correct: bool, attempts: n}
    orderDone: 0,
    currentIndex: 0,
    blockingSeek: true,
  };

  const storageKey = `resources:lesson:${slug}:state`;
  try { const saved = sessionStorage.getItem(storageKey); if (saved) state = Object.assign(state, JSON.parse(saved)); } catch(e) {}

  fetch(endpoints.schema, { credentials: 'same-origin' })
    .then(r => r.json())
    .then(data => {
      schema = data;
      // hydrate from server progress
      if (data.progress) {
        state.orderDone = data.progress.last_answered_question_order || 0;
        if (data.progress.last_video_time) video.currentTime = data.progress.last_video_time;
      }
      bindVideo();
    })
    .catch(err => console.error('Failed to load lesson schema', err));

  function bindVideo(){
    video.addEventListener('timeupdate', onTimeUpdate);
    video.addEventListener('seeking', onSeeking);
    if (openSubmit) openSubmit.addEventListener('click', submitOpenEnded);
    if (completeClose) completeClose.addEventListener('click', closeCompletion);
  }

  function onTimeUpdate(){
    persistProgress(false);
    const nextQ = nextUnansweredQuestion();
    if (!nextQ) return; // all done
    const t = video.currentTime;
    if (t >= nextQ.timestamp_seconds - 0.1) {
      video.pause();
      showQuestion(nextQ);
    }
  }

  function onSeeking(e){
    const nextQ = nextUnansweredQuestion();
    if (!nextQ) return; // allow free seek after completion
    const target = video.currentTime;
    if (target > nextQ.timestamp_seconds - 0.2) {
      // snap back to just before checkpoint
      video.currentTime = Math.max(0, nextQ.timestamp_seconds - 0.5);
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
      current_time: video.currentTime,
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
        setTimeout(()=>{ hideDialog(); resumeVideoSlightly(); persistProgress(true); }, 550);
      } else {
        showFeedback('Try Again', false);
        persistProgress(false);
      }
    }).catch(()=>{
      // offline fallback: optimistic update but don't advance
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
      current_time: video.currentTime,
    };
    postJSON(endpoints.attempt, body).then(res => {
      const qst = state.answered[q.id] || { attempts: 0 };
      qst.attempts = (qst.attempts||0) + 1;
      qst.correct = false; // not scored
      qst.completed = true; // completion on submit
      state.answered[q.id] = qst;
      showFeedback('Saved', true);
      state.orderDone = Math.max(state.orderDone, q.order);
      setTimeout(()=>{ hideDialog(); resumeVideoSlightly(); persistProgress(true); }, 550);
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

  function resumeVideoSlightly(){
    video.currentTime = Math.min(video.duration, video.currentTime + 0.2);
    // If all answered, show completion
    const nextQ = nextUnansweredQuestion();
    if (!nextQ) {
      showCompletion();
    } else {
      video.play().catch(()=>{});
    }
  }

  function showCompletion(){
    const correct = (schema && schema.lesson) ? (schema.progress && schema.progress.correct_count) : 0;
    // recompute locally from state if needed
    let localCorrect = 0; const scoredCount = (schema.questions||[]).filter(q => q.is_scored).length;
    (schema.questions||[]).forEach(q => { if (q.is_scored && state.answered[q.id] && state.answered[q.id].completed && state.answered[q.id].correct) localCorrect++; });
    const correctCount = Number.isFinite(correct) && correct >= localCorrect ? correct : localCorrect;
    completeSummary.textContent = `You answered ${correctCount} of ${scoredCount} correctly. Keep building your skills with ReRoute Learn.`;

    completeOverlay.hidden = false; completeOverlay.setAttribute('aria-hidden','false');
    completeDialog.hidden = false; completeDialog.setAttribute('aria-hidden','false');
    postJSON(endpoints.progress, {
      last_video_time: video.currentTime,
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
      postJSON(endpoints.progress, {
        last_video_time: video.currentTime,
        last_answered_question_order: state.orderDone,
        raw_state: state,
      }).catch(()=>{});
    }
  }

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
})();

