// Imported resume preview editor: inline edit, reorder, undo/redo, save/discard
(function(){
  const $ = (sel, root=document) => root.querySelector(sel);
  const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));

  const editor = $('#editor');
  if (!editor) return;

  const toolbar = $('.editor-toolbar');
  const updateUrl = toolbar?.dataset.updateUrl || '';
  const discardUrl = toolbar?.dataset.discardUrl || '';
  const csrf = decodeURIComponent(window.RR_CSRF || '');

  // History stack for undo/redo
  const history = [];
  const future = [];

  function snapshot(){
    const data = serialize();
    history.push(JSON.stringify(data));
    if (history.length > 100) history.shift();
    // clear redo stack on new change
    future.length = 0;
    updateUndoRedo();
  }

  function restore(json){
    try {
      const state = JSON.parse(json);
      applyState(state);
    } catch {}
  }

  function updateUndoRedo(){
    const undoBtn = $('#undoBtn');
    const redoBtn = $('#redoBtn');
    if (undoBtn) undoBtn.disabled = history.length <= 1; // first is initial
    if (redoBtn) redoBtn.disabled = future.length === 0;
  }

  function initHistory(){
    history.length = 0; future.length = 0;
    history.push(JSON.stringify(serialize()));
    updateUndoRedo();
  }

  // Track deletes for rows and skills
  const deletes = { exp: new Set(), edu: new Set(), skill: new Set() };
  let newCounters = { exp: 0, edu: 0, skill: 0 };

  function serialize(){
    const sectionOrder = $$('.resume-section.draggable').map(s => s.dataset.section);
    const summary = $('#field-summary')?.innerText || '';

    const expRows = $$('#experienceList .editable-row');
    const experiences_updates = [];
    const experiences_creates = [];
    expRows.forEach(li => {
      const obj = {
        id: li.dataset.id,
        job_title: $('[data-field="job_title"]', li)?.innerText || '',
        company: $('[data-field="company"]', li)?.innerText || '',
        dates: $('[data-field="dates"]', li)?.innerText || ''
      };
      if (!obj.id || obj.id.startsWith('new-exp-')) {
        // Only create if required fields present
        if (obj.job_title.trim() && obj.company.trim()) {
          experiences_creates.push({ job_title: obj.job_title, company: obj.company, dates: obj.dates });
        }
      } else {
        experiences_updates.push(obj);
      }
    });

    const eduRows = $$('#educationList .editable-row');
    const education_updates = [];
    const education_creates = [];
    eduRows.forEach(li => {
      const obj = {
        id: li.dataset.id,
        degree: $('[data-field="degree"]', li)?.innerText || '',
        school_name: $('[data-field="school_name"]', li)?.innerText || '',
        graduation_year: $('[data-field="graduation_year"]', li)?.innerText || ''
      };
      if (!obj.id || obj.id.startsWith('new-edu-')) {
        if (obj.school_name.trim()) {
          education_creates.push({ degree: obj.degree, school_name: obj.school_name, graduation_year: obj.graduation_year });
        }
      } else {
        education_updates.push(obj);
      }
    });

    const skillEls = $$('#skillsList [data-model="skill"]');
    const skills_updates = [];
    const skills_creates = [];
    skillEls.forEach(el => {
      const id = el.dataset.id;
      const name = (el.innerText || '').replace(/×\s*$/, '').trim();
      if (!id || id.startsWith('new-skill-')) {
        if (name) skills_creates.push({ name });
      } else {
        skills_updates.push({ id, name });
      }
    });

    // Persist row order (for future rendering) and deletes
    const experience_order = expRows.map(li => li.dataset.id).filter(Boolean);
    const education_order = eduRows.map(li => li.dataset.id).filter(Boolean);

    return {
      section_order: sectionOrder, summary,
      experiences_updates, experiences_creates, experience_deletes: Array.from(deletes.exp), experience_order,
      education_updates, education_creates, education_deletes: Array.from(deletes.edu), education_order,
      skills_updates, skills_creates, skill_deletes: Array.from(deletes.skill)
    };
  }

  function applyState(state){
    try {
      if (state.summary != null) $('#field-summary').innerText = state.summary;
      if (Array.isArray(state.experiences)) {
        state.experiences.forEach(item => {
          const row = $(`#experienceList .editable-row[data-id="${item.id}"]`);
          if (!row) return;
          $('[data-field="job_title"]', row).innerText = item.job_title || '';
          $('[data-field="company"]', row).innerText = item.company || '';
          $('[data-field="dates"]', row).innerText = item.dates || '';
        });
      }
      if (Array.isArray(state.education)) {
        state.education.forEach(item => {
          const row = $(`#educationList .editable-row[data-id="${item.id}"]`);
          if (!row) return;
          $('[data-field="degree"]', row).innerText = item.degree || '';
          $('[data-field="school_name"]', row).innerText = item.school_name || '';
          $('[data-field="graduation_year"]', row).innerText = item.graduation_year || '';
        });
      }
      if (Array.isArray(state.section_order)) {
        const map = new Map(state.section_order.map((s, i) => [s, i]));
        const sections = $$('.resume-section.draggable');
        sections.sort((a,b)=> (map.get(a.dataset.section)||0) - (map.get(b.dataset.section)||0))
                .forEach(s => s.parentNode.appendChild(s));
      }
    } catch {}
  }

  // Drag-and-drop reordering of sections and rows
  function makeDraggable(containerSel){
    const container = $(containerSel);
    if (!container) return;
    let dragged = null;
    container.addEventListener('dragstart', e => {
      const li = e.target.closest('.draggable, .editable-row');
      if (!li) return;
      dragged = li; li.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
    });
    container.addEventListener('dragover', e => {
      if (!dragged) return; e.preventDefault();
      const siblings = Array.from(container.children).filter(el => el !== dragged && (el.classList.contains('draggable') || el.classList.contains('editable-row')));
      const y = e.clientY;
      let next = null;
      for (const s of siblings){ const rect = s.getBoundingClientRect(); if (y < rect.top + rect.height/2) { next = s; break; } }
      container.insertBefore(dragged, next);
    });
    container.addEventListener('dragend', () => {
      if (dragged) dragged.classList.remove('dragging');
      dragged = null; snapshot();
    });
  }

  makeDraggable('#editor');
  makeDraggable('#experienceList');
  makeDraggable('#educationList');

  // Content changes
  $$('.editable').forEach(el => {
    el.addEventListener('input', () => snapshot());
  });

  // Add / Remove handlers
  function createExpRow(){
    const id = `new-exp-${++newCounters.exp}`;
    const li = document.createElement('li');
    li.className = 'editable-row';
    li.dataset.model = 'experience';
    li.dataset.id = id;
    li.innerHTML = `
      <div class="row-line">
        <span class="drag-handle" aria-hidden="true">⋮</span>
        <span class="inline editable" contenteditable="true" data-field="job_title">Job Title</span>
        —
        <span class="inline editable" contenteditable="true" data-field="company">Company</span>
        <span class="inline muted">(</span>
        <span class="inline editable" contenteditable="true" data-field="dates"></span>
        <span class="inline muted">)</span>
        <button type="button" class="remove-row" title="Remove">×</button>
      </div>`;
    // attach input listener for new editables
    $$('.editable', li).forEach(el => el.addEventListener('input', () => snapshot()));
    return li;
  }
  function createEduRow(){
    const id = `new-edu-${++newCounters.edu}`;
    const li = document.createElement('li');
    li.className = 'editable-row';
    li.dataset.model = 'education';
    li.dataset.id = id;
    li.innerHTML = `
      <div class="row-line">
        <span class="drag-handle" aria-hidden="true">⋮</span>
        <span class="inline editable" contenteditable="true" data-field="degree">Education/Training</span>
        —
        <span class="inline editable" contenteditable="true" data-field="school_name">School</span>
        <span class="inline muted">(</span>
        <span class="inline editable" contenteditable="true" data-field="graduation_year"></span>
        <span class="inline muted">)</span>
        <button type="button" class="remove-row" title="Remove">×</button>
      </div>`;
    $$('.editable', li).forEach(el => el.addEventListener('input', () => snapshot()));
    return li;
  }
  function createSkillPill(){
    const id = `new-skill-${++newCounters.skill}`;
    const li = document.createElement('li');
    li.className = 'skill-pill editable';
    li.dataset.model = 'skill';
    li.dataset.id = id;
    li.dataset.field = 'name';
    li.contentEditable = 'true';
    li.textContent = 'New Skill';
    const btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'remove-row small'; btn.title = 'Remove'; btn.textContent = '×';
    li.appendChild(btn);
    li.addEventListener('input', () => snapshot());
    return li;
  }

  editor.addEventListener('click', (e) => {
    const addExp = e.target.closest('.add-exp');
    if (addExp){ $('#experienceList').appendChild(createExpRow()); snapshot(); return; }
    const addEdu = e.target.closest('.add-edu');
    if (addEdu){ $('#educationList').appendChild(createEduRow()); snapshot(); return; }
    const addSkill = e.target.closest('.add-skill');
    if (addSkill){ $('#skillsList').appendChild(createSkillPill()); snapshot(); return; }
    const removeBtn = e.target.closest('.remove-row');
    if (removeBtn){
      const row = removeBtn.closest('.editable-row, [data-model="skill"]');
      if (!row) return;
      const id = row.dataset.id;
      const model = row.dataset.model;
      if (id && !id.startsWith('new-')){
        if (model === 'experience') deletes.exp.add(id);
        else if (model === 'education') deletes.edu.add(id);
        else if (model === 'skill') deletes.skill.add(id);
      }
      row.remove();
      snapshot();
    }
  });

  // Undo/Redo/Reset
  $('#undoBtn')?.addEventListener('click', () => {
    if (history.length <= 1) return;
    const curr = history.pop();
    future.push(curr);
    restore(history[history.length - 1]);
    updateUndoRedo();
  });
  $('#redoBtn')?.addEventListener('click', () => {
    if (!future.length) return;
    const state = future.pop();
    history.push(state);
    restore(state);
    updateUndoRedo();
  });
  $('#resetBtn')?.addEventListener('click', () => {
    // reload page state
    window.location.reload();
  });

  async function saveDraft(){
    const payload = serialize();
    const res = await fetch(updateUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf,
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Save failed');
    return res.json();
  }

  $('#saveDraftBtn')?.addEventListener('click', () => {
    saveDraft().then(() => {
      toast('Changes saved');
    }).catch(() => alert('Failed to save changes.'));
  });
  $('#saveDraftBtn2')?.addEventListener('click', () => {
    $('#saveDraftBtn')?.click();
  });

  $('#discardBtn')?.addEventListener('click', async () => {
    if (!confirm('Discard this imported resume and delete the draft?')) return;
    const res = await fetch(discardUrl, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest' }
    });
    const data = await res.json();
    if (res.ok && data.redirect_url) window.location.href = data.redirect_url; else alert('Failed to discard.');
  });

  function toast(msg){
    let el = $('#rr-toast');
    if (!el){ el = document.createElement('div'); el.id = 'rr-toast'; document.body.appendChild(el); }
    el.textContent = msg; el.className = 'show';
    setTimeout(()=>{ el.className=''; }, 1500);
  }

  // Initialize
  initHistory();
})();
