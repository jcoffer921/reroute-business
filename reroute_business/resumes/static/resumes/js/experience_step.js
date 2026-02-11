document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('[data-autosave-url]');
  if (!form) return;
  const autosaveUrl = form.dataset.autosaveUrl;
  const savedEl = document.querySelector('[data-saved-text]');
  const list = document.querySelector('[data-role-list]');
  const addBtn = document.querySelector('[data-add-role]');

  const roleTemplate = document.getElementById('role-template');

  function collectRoles() {
    const roles = [];
    list.querySelectorAll('.role-card').forEach((card, index) => {
      roles.push({
        id: card.dataset.roleId || '',
        role_type: card.querySelector('[name$="-role_type"]')?.value || 'job',
        job_title: card.querySelector('[name$="-job_title"]')?.value || '',
        company: card.querySelector('[name$="-company"]')?.value || '',
        start_year: card.querySelector('[name$="-start_year"]')?.value || '',
        end_year: card.querySelector('[name$="-end_year"]')?.value || '',
        currently_work_here: card.querySelector('[name$="-currently_work_here"]')?.checked || false,
        responsibilities: card.querySelector('[name$="-responsibilities"]')?.value || '',
        tools: card.querySelector('[name$="-tools"]')?.value || '',
        delete: card.dataset.deleted === 'true',
        order: index,
      });
    });
    return roles;
  }

  const saveNow = () => {
    return postJSON(autosaveUrl, { roles: collectRoles() })
      .then(() => setSavedText(savedEl, 'Saved'))
      .catch(() => {});
  };

  const doSave = debounce(saveNow, 700);

  function wireCard(card) {
    card.querySelectorAll('input, select, textarea').forEach((el) => {
      el.addEventListener('input', doSave);
      el.addEventListener('change', doSave);
    });
    const removeBtn = card.querySelector('[data-remove-role]');
    if (removeBtn) {
      removeBtn.addEventListener('click', () => {
        card.dataset.deleted = 'true';
        const deleteInput = card.querySelector('[data-delete-input]') || card.querySelector('input[name$="-DELETE"]');
        if (deleteInput) deleteInput.checked = true;
        card.classList.add('is-removed');
        card.style.display = 'none';
        doSave();
      });
    }

    const currentToggle = card.querySelector('[name$=\"-currently_work_here\"]');
    const endYearInput = card.querySelector('[name$=\"-end_year\"]');
    if (currentToggle && endYearInput) {
      const toggleEnd = () => {
        endYearInput.disabled = currentToggle.checked;
        if (currentToggle.checked) {
          endYearInput.value = '';
        }
      };
      currentToggle.addEventListener('change', toggleEnd);
      toggleEnd();
    }
  }

  list.querySelectorAll('.role-card').forEach(wireCard);

  if (addBtn && roleTemplate) {
    addBtn.addEventListener('click', () => {
      const clone = roleTemplate.content.cloneNode(true);
      list.appendChild(clone);
      const newCard = list.querySelector('.role-card:last-child');
      wireCard(newCard);
      doSave();
    });
  }

  form.addEventListener('submit', () => {
    saveNow();
  });
});
