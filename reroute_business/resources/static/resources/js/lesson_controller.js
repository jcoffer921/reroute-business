// Simplified lesson flow: show quiz after video ends (no timestamps)
(function(){
  const $ = (sel) => document.querySelector(sel);
  const endpoints = window.__LESSON_ENDPOINTS__ || {};
  const csrfToken = getCookie('csrftoken');

  const quizContainer = $('#lessonQuizContainer');
  const submitBtn = document.querySelector('#lessonQuizSubmit');
  const resultEl = document.querySelector('#lessonQuizResult');

  let schema = null;
  let useYouTube = false;
  let player = null;
  let ytEndPoll = null;

  fetch(endpoints.schema, { credentials: 'same-origin' })
    .then(r => r.json())
    .then(data => {
      schema = data || {};
      useYouTube = !!(schema && schema.lesson && schema.lesson.youtube_video_id);
      if (useYouTube) bootYouTube(schema.lesson.youtube_video_id);
      else bootHTML5();
      // Immediately render quiz in sidebar
      renderQuiz();
    })
    .catch(()=>{});

  function bootHTML5(){
    const video = $('#lessonVideo');
    if (!video) return;
    try { video.addEventListener('ended', onVideoEnded); } catch(_){ }
    // Fallback: detect near-end via timeupdate if 'ended' doesn't fire reliably
    try {
      let endedOnce = false;
      video.addEventListener('timeupdate', () => {
        if (endedOnce) return;
        const dur = Number(video.duration || 0);
        if (dur && (dur - video.currentTime) <= 0.3) { endedOnce = true; onVideoEnded(); }
      });
    } catch(_){ }
  }

  function bootYouTube(videoId){
    const YT_ID = videoId || window.__LESSON_YT_ID__;
    if (!YT_ID) return;
    loadYouTubeAPI(() => {
      // eslint-disable-next-line no-undef
      player = new YT.Player('ytPlayer', {
        videoId: YT_ID,
        playerVars: { playsinline:1, rel:0, modestbranding:1, origin: window.location.origin },
        events: {
          onStateChange: (ev) => {
            try { if (typeof YT !== 'undefined' && ev.data === YT.PlayerState.ENDED) onVideoEnded(); } catch(_){ }
            // Fallback: start/stop near-end poll
            try {
              if (typeof YT !== 'undefined' && ev.data === YT.PlayerState.PLAYING) {
                if (ytEndPoll) clearInterval(ytEndPoll);
                ytEndPoll = setInterval(() => {
                  try {
                    const dur = typeof player.getDuration === 'function' ? player.getDuration() : 0;
                    const cur = typeof player.getCurrentTime === 'function' ? player.getCurrentTime() : 0;
                    if (dur && (dur - cur) <= 0.35) { clearInterval(ytEndPoll); ytEndPoll = null; onVideoEnded(); }
                  } catch(_){ }
                }, 500);
              } else if (typeof YT !== 'undefined' && ev.data === YT.PlayerState.PAUSED) {
                // keep polling during pause as user might be at the end
              } else {
                if (ytEndPoll) { clearInterval(ytEndPoll); ytEndPoll = null; }
              }
            } catch(_){ }
          }
        }
      });
    });
  }

  function onVideoEnded(){ /* no-op: quiz is available anytime */ }

  function renderQuiz(){
    if (!quizContainer || !schema) return;
    quizContainer.innerHTML = '';
    const qs = (schema.questions || []);
    qs.forEach(q => {
      const box = document.createElement('div');
      box.className = 'lesson-quiz-question';
      const h = document.createElement('h3'); h.textContent = q.prompt || '';
      box.appendChild(h);
      if (q.qtype === 'MULTIPLE_CHOICE'){
        const list = document.createElement('div'); list.className='lesson-quiz-choices';
        (q.choices||[]).forEach(ch => {
          const id = `q${q.id}_${ch.id}`;
          const label = document.createElement('label'); label.setAttribute('for', id); label.classList.add('rr-flex-row-8');
          const inp = document.createElement('input'); inp.type='radio'; inp.name=`q_${q.id}`; inp.value = ch.id; inp.id = id;
          label.appendChild(inp);
          const span = document.createElement('span'); span.textContent = `${(ch.label||'').toUpperCase()}) ${ch.text||''}`; label.appendChild(span);
          list.appendChild(label);
        });
        box.appendChild(list);
      } else {
        const ta = document.createElement('textarea'); ta.rows=3; ta.name=`t_${q.id}`; ta.placeholder='Type your answer...'; ta.classList.add('rr-w-100');
        box.appendChild(ta);
      }
      quizContainer.appendChild(box);
    });

    // Use existing sidebar action controls
    if (quizContainer) { quizContainer.hidden = false; }
    if (submitBtn) {
      // Prevent duplicate bindings on hot reloads
      submitBtn.onclick = () => submitQuiz(qs, resultEl);
    }
  }

  function submitQuiz(qs, resultEl){
    const tasks = [];
    let scoredTotal = 0; let correctCount = 0;
    qs.forEach(q => {
      if (q.qtype === 'MULTIPLE_CHOICE'){
        const sel = document.querySelector(`input[name="q_${q.id}"]:checked`);
        if (!sel) return; // unanswered -> ignore
        if (q.is_scored) scoredTotal++;
        tasks.push(postJSON(endpoints.attempt, { question_id: q.id, selected_choice_id: sel.value })
          .then(resp => { if (q.is_scored && resp && resp.is_correct) correctCount++; })
          .catch(()=>{}));
      } else {
        const ta = document.querySelector(`textarea[name="t_${q.id}"]`);
        const text = (ta && ta.value || '').trim(); if (!text) return;
        tasks.push(postJSON(endpoints.attempt, { question_id: q.id, open_text: text }).catch(()=>{}));
      }
    });
    Promise.all(tasks).then(() => {
      if (resultEl) resultEl.textContent = `You answered ${correctCount} of ${scoredTotal} correctly.`;
    });
  }

  function postJSON(url, body){
    return fetch(url, { method:'POST', headers:{ 'Content-Type':'application/json', 'X-CSRFToken': csrfToken }, credentials:'same-origin', body: JSON.stringify(body||{}) })
      .then(r => { if (!r.ok) throw new Error('Bad response'); return r.json(); });
  }

  function getCookie(name){ let v=null; if(document.cookie&&document.cookie!==''){ const cookies=document.cookie.split(';'); for(let i=0;i<cookies.length;i++){ const c=cookies[i].trim(); if(c.substring(0,name.length+1)===(name+'=')){ v=decodeURIComponent(c.substring(name.length+1)); break; } } } return v; }

  function loadYouTubeAPI(cb){ if (window.YT && window.YT.Player){ cb(); return; } const tag=document.createElement('script'); tag.src='https://www.youtube.com/iframe_api'; const first=document.getElementsByTagName('script')[0]; first.parentNode.insertBefore(tag, first); const prev=window.onYouTubeIframeAPIReady; window.onYouTubeIframeAPIReady=function(){ if (typeof prev==='function') { try{ prev(); } catch(_){ } } cb(); } }
})();
