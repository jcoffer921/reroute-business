document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('[data-autosave-url]');
  if (!form) return;
  const autosaveUrl = form.dataset.autosaveUrl;
  const savedEl = document.querySelector('[data-saved-text]');

  const sections = document.querySelectorAll('[data-skill-section]');

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
    const list = readList(section);
    renderTags(section, list);

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

    section.querySelectorAll('.resume-pill').forEach((pill) => {
      pill.addEventListener('click', () => {
        const value = pill.dataset.value || pill.textContent.trim();
        const listNow = readList(section);
        if (!listNow.some((item) => item.toLowerCase() === value.toLowerCase())) {
          listNow.push(value);
          writeList(section, listNow);
          doSave();
        }
      });
    });
  });

  form.addEventListener('submit', () => {
    saveNow();
  });
});
