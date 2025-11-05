// Inline interactive questions for Video Library cards
(function(){
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
    document.head.appendChild(tag);
    const prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = function(){
      if (typeof prev === 'function') { try { prev(); } catch(e){} }
      cb();
    };
  }

  function initCard(card){
    const iframe = card.querySelector('iframe.yt-embed');
    if (!iframe) return;
    const hasLesson = card.hasAttribute('data-lesson');
    if (!hasLesson) return; // no interactive layer needed

    const schemaUrl = card.getAttribute('data-schema-url');
    const attemptUrl = card.getAttribute('data-attempt-url');
    const progressUrl = card.getAttribute('data-progress-url');

    const overlay = card.querySelector('.lesson-overlay:not(.lesson-complete-overlay)');
    const dialog = card.querySelector('.lesson-dialog');
    const promptEl = card.querySelector('.lesson-prompt');
    const choicesEl = card.querySelector('.lesson-choices');
    const openWrap = card.querySelector('.lesson-open-ended');
    const openArea = card.querySelector('.lesson-textarea');
    const openSubmit = card.querySelector('.lesson-submit-open');
    const feedbackEl = card.querySelector('.lesson-feedback');
    const completeOverlay = card.querySelector('.lesson-complete-overlay');
    const completeDialog = card.querySelector('.lesson-complete');
    const completeSummary = card.querySelector('.lesson-complete-summary');
    const completeClose = card.querySelector('.lesson-complete-close');

    let schema = null;
    let player = null;
    let poll = null;
    let state = { answered: {}, orderDone: 0 };
    const storageKey = 'gallery:lesson:' + (card.getAttribute('data-lesson-slug') || '') + ':state';
    try { const saved = sessionStorage.getItem(storageKey); if (saved) state = Object.assign(state, JSON.parse(saved)); } catch(e){}

    function currentTime(){
      try { return (player && typeof player.getCurrentTime === 'function') ? player.getCurrentTime() : 0; } catch(e){ return 0; }
    }
    function play(){ try { player.playVideo(); } catch(e){} }
    function pause(){ try { player.pauseVideo(); } catch(e){} }
    function seekTo(t){ try { player.seekTo(Math.max(0, t), true); } catch(e){} }

    function showDialog(){ dialog.hidden = false; dialog.setAttribute('aria-hidden','false'); overlay.hidden = false; overlay.setAttribute('aria-hidden','false'); }
    function hideDialog(){ dialog.hidden = true; dialog.setAttribute('aria-hidden','true'); overlay.hidden = true; overlay.setAttribute('aria-hidden','true'); feedbackEl.textContent = ''; }
    function showCompletion(correctCount, scoredCount){
      completeSummary.textContent = 'Lesson Complete – Great work! You answered ' + correctCount + ' of ' + scoredCount + ' correctly.';
      completeOverlay.hidden = false; completeOverlay.setAttribute('aria-hidden','false');
      completeDialog.hidden = false; completeDialog.setAttribute('aria-hidden','false');
    }
    function hideCompletion(){ completeDialog.hidden = true; completeDialog.setAttribute('aria-hidden','true'); completeOverlay.hidden = true; completeOverlay.setAttribute('aria-hidden','true'); }

    function postJSON(url, body){
      return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        credentials: 'same-origin',
        body: JSON.stringify(body || {}),
      }).then(r => { if (!r.ok) throw new Error('Bad response'); return r.json(); });
    }

    function renderQuestion(q){
      promptEl.textContent = q.prompt;
      feedbackEl.textContent = '';
      choicesEl.innerHTML = '';
      openWrap.hidden = true;
      if (q.qtype === 'MULTIPLE_CHOICE'){
        (q.choices || []).forEach(c => {
          const btn = document.createElement('button');
          btn.className = 'lesson-btn';
          btn.textContent = (c.label || '') + ' ' + (c.text || '');
          btn.addEventListener('click', () => {
            postJSON(attemptUrl, { question_id: q.id, selected_choice_id: c.id, current_time: currentTime() })
              .then(resp => {
                const correct = !!resp.is_correct;
                const qst = state.answered[q.id] || { attempts: 0 };
                qst.attempts = (qst.attempts||0) + 1;
                qst.correct = correct;
                qst.completed = true;
                state.answered[q.id] = qst;
                feedbackEl.textContent = correct ? 'Correct!' : 'Saved';
                if (correct){ setTimeout(()=>{ hideDialog(); resumeSlightly(); persist(true); }, 500); }
                else { setTimeout(()=>{ hideDialog(); resumeSlightly(); persist(true); }, 500); }
              })
              .catch(()=>{ feedbackEl.textContent = 'Network error.'; });
          });
          choicesEl.appendChild(btn);
        });
      } else {
        openWrap.hidden = false;
        openArea.value = '';
      }
      showDialog();
    }

    function nextUnanswered(){
      const qs = (schema && schema.questions) || [];
      for (let i=0;i<qs.length;i++){
        const q = qs[i];
        const st = state.answered[q.id];
        if (!st || !st.completed) return q;
      }
      return null;
    }

    function onTick(){
      const t = currentTime();
      const q = nextUnanswered();
      if (!q) return; // done
      if (t >= (q.timestamp_seconds - 0.05)){
        pause();
        renderQuestion(q);
      }
    }

    function startPoll(){ stopPoll(); poll = setInterval(onTick, 400); }
    function stopPoll(){ if (poll) { clearInterval(poll); poll = null; } }

    function resumeSlightly(){ seekTo(currentTime() + 0.2); play(); }

    function persist(flush){
      try { sessionStorage.setItem(storageKey, JSON.stringify(state)); } catch(e){}
      if (flush){
        const scored = (schema.questions||[]).filter(q => q.is_scored).length;
        let correct = 0; (schema.questions||[]).forEach(q => { const st = state.answered[q.id]; if (q.is_scored && st && st.correct) correct++; });
        postJSON(progressUrl, { last_video_time: currentTime(), last_answered_question_order: 0, raw_state: state, completed: (!nextUnanswered()) })
          .catch(()=>{});
        if (!nextUnanswered()) showCompletion(correct, scored);
      }
    }

    if (openSubmit){
      openSubmit.addEventListener('click', () => {
        const q = nextUnanswered();
        const text = (openArea && openArea.value || '').trim();
        if (!q || !text) return;
        postJSON(attemptUrl, { question_id: q.id, open_text: text, current_time: currentTime() })
          .then(() => {
            const qst = state.answered[q.id] || { attempts: 0 };
            qst.attempts = (qst.attempts||0) + 1;
            qst.correct = false; qst.completed = true;
            state.answered[q.id] = qst;
            hideDialog(); resumeSlightly(); persist(true);
          })
          .catch(()=>{ feedbackEl.textContent = 'Network error.'; });
      });
    }
    if (completeClose){ completeClose.addEventListener('click', hideCompletion); }

    // Boot: load schema, then player
    fetch(schemaUrl, { credentials: 'same-origin' }).then(r => r.json()).then(data => {
      schema = data || {};
      loadYouTubeAPI(() => {
        // eslint-disable-next-line no-undef
        player = new YT.Player(iframe.id, {
          events: {
            onReady: () => { startPoll(); },
            onStateChange: (ev) => { if (ev.data === 1) startPoll(); else if (ev.data === 2) stopPoll(); }
          }
        });
      });
    }).catch(()=>{});
  }

  function initModal(modal){
    if (!modal || !modal.hasAttribute('data-lesson')) return;
    const iframeId = modal.getAttribute('data-iframe-id');
    const iframe = iframeId ? document.getElementById(iframeId) : null;
    if (!iframe) return;

    const schemaUrl = modal.getAttribute('data-schema-url');
    const attemptUrl = modal.getAttribute('data-attempt-url');
    const progressUrl = modal.getAttribute('data-progress-url');

    const overlay = modal.querySelector('.lesson-overlay:not(.lesson-complete-overlay)');
    const dialog = modal.querySelector('.lesson-dialog');
    const promptEl = modal.querySelector('.lesson-prompt');
    const choicesEl = modal.querySelector('.lesson-choices');
    const openWrap = modal.querySelector('.lesson-open-ended');
    const openArea = modal.querySelector('.lesson-textarea');
    const openSubmit = modal.querySelector('.lesson-submit-open');
    const feedbackEl = modal.querySelector('.lesson-feedback');
    const completeOverlay = modal.querySelector('.lesson-complete-overlay');
    const completeDialog = modal.querySelector('.lesson-complete');
    const completeSummary = modal.querySelector('.lesson-complete-summary');
    const completeClose = modal.querySelector('.lesson-complete-close');

    // Clean up any previous session
    try { if (modal.__quizPoll) { clearInterval(modal.__quizPoll); modal.__quizPoll = null; } } catch(_){ }
    try { if (modal.__ytPlayer && typeof modal.__ytPlayer.destroy === 'function') { modal.__ytPlayer.destroy(); modal.__ytPlayer = null; } } catch(_){ }

    let schema = null; let player = null; let poll = null;
    function currentTime(){ try { return (player && typeof player.getCurrentTime==='function') ? player.getCurrentTime() : 0; } catch(e){ return 0; } }
    function pause(){ try { player.pauseVideo(); } catch(e){} }
    function play(){ try { player.playVideo(); } catch(e){} }
    function seekTo(t){ try { player.seekTo(Math.max(0,t), true); } catch(e){} }

    function showDialog(){ if (!dialog||!overlay) return; dialog.hidden=false; dialog.setAttribute('aria-hidden','false'); overlay.hidden=false; overlay.setAttribute('aria-hidden','false'); }
    function hideDialog(){ if (!dialog||!overlay) return; dialog.hidden=true; dialog.setAttribute('aria-hidden','true'); overlay.hidden=true; overlay.setAttribute('aria-hidden','true'); if(feedbackEl) feedbackEl.textContent=''; }
    function showCompletion(correct, scored){ if(!completeOverlay||!completeDialog) return; if(completeSummary) completeSummary.textContent = 'Lesson Complete – Great work! You answered ' + correct + ' of ' + scored + ' correctly.'; completeOverlay.hidden=false; completeOverlay.setAttribute('aria-hidden','false'); completeDialog.hidden=false; completeDialog.setAttribute('aria-hidden','false'); }
    function hideCompletion(){ if(!completeOverlay||!completeDialog) return; completeDialog.hidden=true; completeDialog.setAttribute('aria-hidden','true'); completeOverlay.hidden=true; completeOverlay.setAttribute('aria-hidden','true'); }
    function postJSON(url, body){ return fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')},credentials:'same-origin',body:JSON.stringify(body||{})}).then(r=>{ if(!r.ok) throw new Error('Bad'); return r.json(); }); }

    const QUIZ_DEBUG = /(?:\?|&)quizdebug=(1|true)/i.test(location.search);
    function nextUnanswered(){ const qs=(schema&&schema.questions)||[]; for(let i=0;i<qs.length;i++){ const q=qs[i]; if(!q || !q.id) continue; const done = modal.__answered && modal.__answered[q.id]; if(!done || !done.completed) return q; } return null; }
    function onTick(){
      const q=nextUnanswered();
      if(!q) return; 
      const t=currentTime();
      // Use a slightly wider threshold than the poll interval to avoid skipping
      if(t >= (q.timestamp_seconds-0.3)){
        if (QUIZ_DEBUG) console.log('[QUIZ] trigger @', t.toFixed(2), '>=', (q.timestamp_seconds-0.3).toFixed(2), 'for q', q.id);
        pause(); renderQuestion(q);
      }
    }
    function start(){ if(poll) clearInterval(poll); poll=setInterval(onTick, 400); modal.__quizPoll = poll; }
    function resumeSlightly(){ seekTo(currentTime()+0.2); play(); }
    function persist(flush){ if(flush){ const qs=(schema&&schema.questions)||[]; const scored=qs.filter(x=>x.is_scored).length; let correct=0; qs.forEach(x=>{ const st=modal.__answered && modal.__answered[x.id]; if(x.is_scored && st && st.correct) correct++; }); postJSON(progressUrl,{ last_video_time: currentTime(), last_answered_question_order: 0, raw_state: modal.__answered||{}, completed: (!nextUnanswered()) }).catch(()=>{}); if(!nextUnanswered()) showCompletion(correct, scored); } }

    function renderQuestion(q){ if(!promptEl) return; promptEl.textContent = q.prompt; if(feedbackEl) feedbackEl.textContent=''; if(choicesEl) choicesEl.innerHTML=''; if(openWrap) openWrap.hidden=true; if(q.qtype==='MULTIPLE_CHOICE'){ (q.choices||[]).forEach(c=>{ const btn=document.createElement('button'); btn.className='lesson-btn'; btn.textContent=(c.label||'')+' '+(c.text||''); btn.addEventListener('click',()=>{ postJSON(attemptUrl,{ question_id:q.id, selected_choice_id:c.id, current_time: currentTime() }).then(resp=>{ modal.__answered = modal.__answered || {}; const st=modal.__answered[q.id] || { attempts:0 }; st.attempts++; st.completed=true; st.correct=!!resp.is_correct; modal.__answered[q.id]=st; if(feedbackEl) feedbackEl.textContent = st.correct ? 'Correct!' : 'Saved'; setTimeout(()=>{ hideDialog(); resumeSlightly(); persist(true); }, 480); }).catch(()=>{ if(feedbackEl) feedbackEl.textContent='Network error.'; }); }); choicesEl.appendChild(btn); }); } else { if(openWrap) openWrap.hidden=false; if(openArea) openArea.value=''; }
      showDialog(); }

    if(openSubmit){ openSubmit.addEventListener('click',()=>{ const q=nextUnanswered(); const text=(openArea&&openArea.value||'').trim(); if(!q||!text) return; postJSON(attemptUrl,{ question_id:q.id, open_text:text, current_time: currentTime() }).then(()=>{ modal.__answered = modal.__answered || {}; const st=modal.__answered[q.id] || { attempts:0 }; st.attempts++; st.completed=true; st.correct=false; modal.__answered[q.id]=st; hideDialog(); resumeSlightly(); persist(true); }).catch(()=>{ if(feedbackEl) feedbackEl.textContent='Network error.'; }); }); }
    if(completeClose){ completeClose.addEventListener('click', hideCompletion); }

    fetch(schemaUrl, { credentials:'same-origin' }).then(r=>r.json()).then(data=>{
      modal.__answered = modal.__answered || {};
      schema = data || {};
      if (QUIZ_DEBUG && schema && Array.isArray(schema.questions)){
        try{
          console.log('[QUIZ] loaded schema with timestamps:', schema.questions.map(q=>({id:q.id, t:q.timestamp_seconds})));
        }catch(_){ }
      }
      loadYouTubeAPI(()=>{
        // eslint-disable-next-line no-undef
        player = new YT.Player(iframe.id, { events: { onReady: ()=>{ start(); }, onStateChange: (ev)=>{ if(ev.data===1) start(); else if(ev.data===2){} } } });
        modal.__ytPlayer = player;
      });
    }).catch(()=>{});
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.video-card[data-lesson]')
      .forEach(initCard);
    const modal = document.getElementById('galleryVideoModal');
    const obs = new MutationObserver(()=>{ initModal(document.getElementById('galleryVideoModal')); });
    if (modal){ obs.observe(modal, { attributes:true, attributeFilter:['data-lesson','data-iframe-id'] }); }
  });
})();
