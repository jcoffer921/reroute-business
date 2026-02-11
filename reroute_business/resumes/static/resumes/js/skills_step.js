document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('[data-autosave-url]');
  if (!form) return;
  const autosaveUrl = form.dataset.autosaveUrl;
  const savedEl = document.querySelector('[data-saved-text]');

  const sections = document.querySelectorAll('[data-skill-section]');
  const SUGGESTION_COUNT = 7;

  function readList(section) {
    const input = section.querySelector('[data-skill-input]');
    const raw = (input?.value || '[]');
    try {
      return JSON.parse(raw);
    } catch {
      return [];
    }
  }

  function writeList(section, list) {
    const input = section.querySelector('[data-skill-input]');
    if (input) input.value = JSON.stringify(list);
    renderTags(section, list);
  }

  function renderTags(section, list) {
    const wrap = section.querySelector('[data-tag-list]');
    if (!wrap) return;
    wrap.innerHTML = '';
    list.forEach((skill, index) => {
      const tag = document.createElement('span');
      tag.className = 'resume-tag';
      tag.innerHTML = `${skill}<button type="button" aria-label="Remove">x</button>`;
      tag.querySelector('button').addEventListener('click', () => {
        const next = list.filter((_, i) => i !== index);
        writeList(section, next);
        doSave();
      });
      wrap.appendChild(tag);
    });
  }

  function parseJsonScript(id) {
    const el = document.getElementById(id);
    if (!el) return [];
    try {
      return JSON.parse(el.textContent);
    } catch {
      return [];
    }
  }

  function renderSuggested(section) {
    const wrap = section.querySelector('[data-suggested-list]');
    if (!wrap) return;
    const all = parseJsonScript(section.dataset.suggestedId);
    const shuffled = all.slice().sort(() => 0.5 - Math.random());
    const slice = shuffled.slice(0, SUGGESTION_COUNT);
    wrap.innerHTML = '';
    slice.forEach((skill) => {
      const pill = document.createElement('span');
      pill.className = 'resume-pill';
      pill.dataset.value = skill;
      pill.textContent = `+ ${skill}`;
      pill.addEventListener('click', () => {
        const listNow = readList(section);
        if (!listNow.some((item) => item.toLowerCase() === skill.toLowerCase())) {
          listNow.push(skill);
          writeList(section, listNow);
          doSave();
        }
      });
      wrap.appendChild(pill);
    });
  }

  const saveNow = () => {
    const payload = {
      technical: readList(document.querySelector('[data-skill-section=\"technical\"]')),
      soft: readList(document.querySelector('[data-skill-section=\"soft\"]')),
    };
    return postJSON(autosaveUrl, payload)
      .then(() => setSavedText(savedEl, 'Saved'))
      .catch(() => {});
  };

  const doSave = debounce(saveNow, 700);

  sections.forEach((section) => {
    const input = section.querySelector('[data-skill-entry]');
    const initial = parseJsonScript(section.dataset.initialId);
    writeList(section, initial);
    renderSuggested(section);

    input?.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      const value = input.value.trim();
      if (!value) return;
      const listNow = readList(section);
      if (listNow.some((item) => item.toLowerCase() === value.toLowerCase())) return;
      const next = [...listNow, value];
      input.value = '';
      writeList(section, next);
      doSave();
    });

    const addBtn = section.querySelector('.skill-add-btn');
    addBtn?.addEventListener('click', () => {
      const value = input.value.trim();
      if (!value) return;
      const listNow = readList(section);
      if (listNow.some((item) => item.toLowerCase() === value.toLowerCase())) return;
      listNow.push(value);
      input.value = '';
      writeList(section, listNow);
      doSave();
    });

    const refreshBtn = section.querySelector('.skill-refresh-btn');
    refreshBtn?.addEventListener('click', () => {
      renderSuggested(section);
    });
  });

  form.addEventListener('submit', () => {
    saveNow();
  });
});
