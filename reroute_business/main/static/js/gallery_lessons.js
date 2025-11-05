// Simplified: show quiz after video ends in gallery modal
(function(){
  function getCookie(name){ let v=null; if(document.cookie&&document.cookie!==''){ const cookies=document.cookie.split(';'); for(let i=0;i<cookies.length;i++){ const c=cookies[i].trim(); if(c.substring(0,name.length+1)===(name+'=')){ v=decodeURIComponent(c.substring(name.length+1)); break; } } } return v; }
  function postJSON(url, body){ return fetch(url,{ method:'POST', headers:{ 'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken') }, credentials:'same-origin', body: JSON.stringify(body||{}) }).then(r=>{ if(!r.ok) throw new Error('Bad'); return r.json(); }); }
  function loadYouTubeAPI(cb){ if (window.YT && window.YT.Player){ cb(); return; } const tag=document.createElement('script'); tag.src='https://www.youtube.com/iframe_api'; document.head.appendChild(tag); const prev=window.onYouTubeIframeAPIReady; window.onYouTubeIframeAPIReady=function(){ if(typeof prev==='function'){ try{ prev(); }catch(_){} } cb(); }; }

  function initModal(modal){
    if (!modal || !modal.hasAttribute('data-lesson')) return;
    const iframeId = modal.getAttribute('data-iframe-id');
    const iframe = iframeId ? document.getElementById(iframeId) : null;
    if (!iframe) return;

    const schemaUrl = modal.getAttribute('data-schema-url');
    const attemptUrl = modal.getAttribute('data-attempt-url');

    const quizActions = document.getElementById('galleryQuizActions');
    const startBtn = document.getElementById('galleryStartQuiz');
    const quizContainer = document.getElementById('galleryQuizContainer');

    // Clean previous
    if (quizActions) quizActions.hidden = true;
    if (quizContainer){ quizContainer.hidden = true; quizContainer.innerHTML=''; }
    try { if (modal.__ytPlayer && typeof modal.__ytPlayer.destroy==='function'){ modal.__ytPlayer.destroy(); modal.__ytPlayer = null; } } catch(_){ }

    let schema = null;
    fetch(schemaUrl, { credentials:'same-origin' })
      .then(r=>r.json()).then(data=>{ schema = data || {}; }).catch(()=>{});

    function showQuizButton(){ if (quizActions) quizActions.hidden = false; }

    if (startBtn){ startBtn.onclick = function(){ if (quizActions) quizActions.hidden = true; renderQuiz(); }; }

    function renderQuiz(){ if(!quizContainer || !schema) return; quizContainer.innerHTML='';
      const qs=(schema.questions||[]);
      qs.forEach(q=>{ const box=document.createElement('div'); box.className='lesson-quiz-question'; const h=document.createElement('h3'); h.textContent=q.prompt||''; box.appendChild(h); if(q.qtype==='MULTIPLE_CHOICE'){ const list=document.createElement('div'); list.className='lesson-quiz-choices'; (q.choices||[]).forEach(ch=>{ const id='mq_'+q.id+'_'+ch.id; const lab=document.createElement('label'); lab.setAttribute('for', id); lab.style.display='flex'; lab.style.alignItems='center'; lab.style.gap='8px'; const inp=document.createElement('input'); inp.type='radio'; inp.name='q_'+q.id; inp.value=ch.id; inp.id=id; lab.appendChild(inp); const span=document.createElement('span'); span.textContent=((ch.label||'').toUpperCase())+') '+(ch.text||''); lab.appendChild(span); list.appendChild(lab); }); box.appendChild(list); } else { const ta=document.createElement('textarea'); ta.rows=3; ta.name='t_'+q.id; ta.placeholder='Type your answer...'; ta.style.width='100%'; box.appendChild(ta); } quizContainer.appendChild(box); });
      const actions=document.createElement('div'); actions.className='lesson-quiz-actions-bar'; const submit=document.createElement('button'); submit.type='button'; submit.className='lesson-btn primary'; submit.textContent='Submit Quiz'; const result=document.createElement('div'); result.className='lesson-quiz-result'; result.style.marginTop='8px'; actions.appendChild(submit); quizContainer.appendChild(actions); quizContainer.appendChild(result); quizContainer.hidden=false; submit.addEventListener('click', ()=>submitQuiz(qs, result)); }

    function submitQuiz(qs, resultEl){ let total=0, correct=0; const tasks=[]; qs.forEach(q=>{ if(q.qtype==='MULTIPLE_CHOICE'){ const sel=document.querySelector('input[name="q_'+q.id+'"]:checked'); if(!sel) return; if(q.is_scored) total++; tasks.push(postJSON(attemptUrl,{ question_id:q.id, selected_choice_id: sel.value }).then(resp=>{ if(q.is_scored && resp && resp.is_correct) correct++; }).catch(()=>{})); } else { const ta=document.querySelector('textarea[name="t_'+q.id+'"]'); const text=(ta&&ta.value||'').trim(); if(!text) return; tasks.push(postJSON(attemptUrl,{ question_id:q.id, open_text:text }).catch(()=>{})); } }); Promise.all(tasks).then(()=>{ if(resultEl) resultEl.textContent='You answered '+correct+' of '+total+' correctly.'; }); }

    // Wire YT ended
    loadYouTubeAPI(()=>{
      // eslint-disable-next-line no-undef
      const player = new YT.Player(iframe.id, { events: { onStateChange: (ev)=>{ try{ if(typeof YT!=='undefined' && ev.data===YT.PlayerState.ENDED){ showQuizButton(); } }catch(_){ } } } });
      modal.__ytPlayer = player;
    });
  }

  document.addEventListener('DOMContentLoaded', function(){
    const modal = document.getElementById('galleryVideoModal');
    const obs = new MutationObserver(()=>{ initModal(document.getElementById('galleryVideoModal')); });
    if (modal){ obs.observe(modal, { attributes:true, attributeFilter:['data-lesson','data-iframe-id'] }); }
  });
})();

