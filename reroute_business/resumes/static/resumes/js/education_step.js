document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('[data-autosave-url]');
  if (!form) return;
  const autosaveUrl = form.dataset.autosaveUrl;
  const savedEl = document.querySelector('[data-saved-text]');
  const list = document.querySelector('[data-education-list]');
  const addBtn = document.querySelector('[data-add-education]');
  const template = document.getElementById('education-template');

  function collect() {
    const education = [];
    list.querySelectorAll('.education-card').forEach((card, index) => {
      education.push({
        id: card.dataset.educationId || '',
        education_type: card.querySelector('[name$=\"-education_type\"]')?.value || '',
        school: card.querySelector('[name$=\"-school\"]')?.value || '',
        field_of_study: card.querySelector('[name$=\"-field_of_study\"]')?.value || '',
        year: card.querySelector('[name$=\"-year\"]')?.value || '',
        details: card.querySelector('[name$=\"-details\"]')?.value || '',
        delete: card.dataset.deleted === 'true',
        order: index,
      });
    });
    return education;
  }

  const saveNow = () => {
    return postJSON(autosaveUrl, { education: collect() })
      .then(() => setSavedText(savedEl, 'Saved'))
      .catch(() => {});
  };

  const doSave = debounce(saveNow, 700);

  function wireCard(card) {
    card.querySelectorAll('input, select, textarea').forEach((el) => {
      el.addEventListener('input', doSave);
      el.addEventListener('change', doSave);
    });
    const removeBtn = card.querySelector('[data-remove-education]');
    if (removeBtn) {
      removeBtn.addEventListener('click', () => {
        card.dataset.deleted = 'true';
        const deleteInput = card.querySelector('[data-delete-input]') || card.querySelector('input[name$="-DELETE"]');
        if (deleteInput) deleteInput.checked = true;
        card.style.display = 'none';
        doSave();
      });
    }
  }

  list.querySelectorAll('.education-card').forEach(wireCard);

  if (addBtn && template) {
    addBtn.addEventListener('click', () => {
      const clone = template.content.cloneNode(true);
      list.appendChild(clone);
      const newCard = list.querySelector('.education-card:last-child');
      wireCard(newCard);
      doSave();
    });
  }

  form.addEventListener('submit', () => {
    saveNow();
  });
});
