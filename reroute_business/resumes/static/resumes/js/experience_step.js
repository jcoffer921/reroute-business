document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('[data-autosave-url]');
  if (!form) return;
  const autosaveUrl = form.dataset.autosaveUrl;
  const savedEl = document.querySelector('[data-saved-text]');
  const list = document.querySelector('[data-role-list]');
  const addBtn = document.querySelector('[data-add-role]');
  const nav = document.querySelector('[data-role-nav]');
  const prevBtn = document.querySelector('[data-role-prev]');
  const nextBtn = document.querySelector('[data-role-next]');
  const countEl = document.querySelector('[data-role-count]');
  let currentIndex = 0;

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

  function getVisibleCards() {
    return [...list.querySelectorAll('.role-card')].filter((card) => card.dataset.deleted !== 'true');
  }

  function updateRoleVisibility() {
    const cards = getVisibleCards();
    if (currentIndex >= cards.length) currentIndex = Math.max(0, cards.length - 1);
    cards.forEach((card, index) => {
      card.classList.toggle('is-active', index === currentIndex);
    });
    if (countEl) {
      countEl.textContent = cards.length ? `Role ${currentIndex + 1} of ${cards.length}` : '';
    }
    if (nav) {
      nav.style.display = cards.length > 1 ? 'flex' : 'none';
    }
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
        updateRoleVisibility();
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
  updateRoleVisibility();

  prevBtn?.addEventListener('click', () => {
    const cards = getVisibleCards();
    if (!cards.length) return;
    currentIndex = Math.max(0, currentIndex - 1);
    updateRoleVisibility();
  });

  nextBtn?.addEventListener('click', () => {
    const cards = getVisibleCards();
    if (!cards.length) return;
    currentIndex = Math.min(cards.length - 1, currentIndex + 1);
    updateRoleVisibility();
  });

  if (addBtn && roleTemplate) {
    addBtn.addEventListener('click', () => {
      const clone = roleTemplate.content.cloneNode(true);
      list.appendChild(clone);
      const newCard = list.querySelector('.role-card:last-child');
      wireCard(newCard);
      currentIndex = getVisibleCards().length - 1;
      updateRoleVisibility();
      doSave();
    });
  }

  form.addEventListener('submit', () => {
    saveNow();
  });
});
