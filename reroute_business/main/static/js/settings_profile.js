(function () {
  const dataEl = document.getElementById('profileSettingsData');
  if (!dataEl) return;

  const urls = {
    avatarUpload: dataEl.dataset.avatarUploadUrl,
    avatarDelete: dataEl.dataset.avatarDeleteUrl,
    backgroundSet: dataEl.dataset.backgroundUrl,
    detailsUpdate: dataEl.dataset.detailsUrl,
    bioUpdate: dataEl.dataset.bioUrl,
    experienceAdd: dataEl.dataset.experienceAddUrl,
    skillAdd: dataEl.dataset.skillAddUrl,
    languageAdd: dataEl.dataset.languageAddUrl,
    experienceDeleteBase: dataEl.dataset.experienceDeleteBaseUrl,
    skillDeleteBase: dataEl.dataset.skillDeleteBaseUrl,
    languageDeleteBase: dataEl.dataset.languageDeleteBaseUrl,
    avatarDefault: dataEl.dataset.avatarDefaultUrl
  };

  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const getCsrfToken = () => {
    const match = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[2]) : '';
  };

  const showToast = (msg, isError) => {
    const toast = document.createElement('div');
    toast.className = 'toast ' + (isError ? '' : 'toast-success');
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
      toast.classList.remove('show');
      toast.addEventListener('transitionend', () => toast.remove(), { once: true });
    }, 2200);
  };

  const request = async (url, options) => {
    const res = await fetch(url, {
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest',
      },
      ...options,
    });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, data };
  };

  // ---------- Modal handling ----------
  let lastFocused = null;
  const openModal = (modal, trigger) => {
    if (!modal) return;
    lastFocused = trigger || document.activeElement;
    modal.classList.add('is-open');
    modal.removeAttribute('hidden');
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');
    const focusTarget = qs('textarea, input, button, [href], select, [tabindex]:not([tabindex="-1"])', modal);
    if (focusTarget) focusTarget.focus({ preventScroll: true });
  };

  const closeModal = (modal) => {
    if (!modal) return;
    modal.classList.remove('is-open');
    modal.setAttribute('hidden', '');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-open');
    if (lastFocused && document.contains(lastFocused)) {
      lastFocused.focus({ preventScroll: true });
    }
  };

  qsa('[data-modal-open]').forEach((btn) => {
    const modalId = btn.getAttribute('data-modal-open');
    const modal = qs(`#${modalId}`);
    if (!modal) return;
    btn.addEventListener('click', () => openModal(modal, btn));
  });

  qsa('.settings-modal').forEach((modal) => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal(modal);
    });
    qsa('[data-modal-close]', modal).forEach((btn) => {
      btn.addEventListener('click', () => closeModal(modal));
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const openModalEl = qs('.settings-modal.is-open');
    if (openModalEl) closeModal(openModalEl);
  });

  // ---------- Avatar upload/delete ----------
  const avatarTrigger = qs('#avatarUploadTrigger');
  const avatarInput = qs('#profileAvatarInput');
  const avatarPreview = qs('#profileAvatarPreview');
  const avatarDeleteBtn = qs('#avatarDeleteBtn');

  if (avatarTrigger && avatarInput) {
    avatarTrigger.addEventListener('click', () => avatarInput.click());
    avatarInput.addEventListener('change', async () => {
      const file = avatarInput.files && avatarInput.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append('avatar', file);
      const { ok, data } = await request(urls.avatarUpload, { method: 'POST', body: formData });
      if (!ok) {
        showToast((data.errors && data.errors.avatar) || 'Upload failed.', true);
        return;
      }
      if (avatarPreview && data.avatar_url) {
        avatarPreview.src = `${data.avatar_url}?v=${Date.now()}`;
      }
      showToast('Profile photo updated.');
    });
  }

  if (avatarDeleteBtn) {
    avatarDeleteBtn.addEventListener('click', async () => {
      if (!confirm('Remove your profile picture?')) return;
      const { ok } = await request(urls.avatarDelete, { method: 'POST' });
      if (!ok) {
        showToast('Unable to remove photo.', true);
        return;
      }
      if (avatarPreview) avatarPreview.src = urls.avatarDefault;
      showToast('Profile photo removed.');
    });
  }

  // ---------- Background gradient ----------
  const gradientPreview = qs('#profileBackgroundPreview');
  qsa('.gradient-option').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const gradient = btn.getAttribute('data-gradient');
      const { ok } = await request(urls.backgroundSet, {
        method: 'POST',
        body: new URLSearchParams({ gradient }),
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
        },
      });
      if (!ok) {
        showToast('Unable to update background.', true);
        return;
      }
      qsa('.gradient-option').forEach((el) => {
        el.classList.remove('selected');
        el.setAttribute('aria-pressed', 'false');
      });
      btn.classList.add('selected');
      btn.setAttribute('aria-pressed', 'true');
      if (gradientPreview) {
        gradientPreview.className = `background-preview__swatch gradient-${gradient}`;
      }
      showToast('Background updated.');
    });
  });

  // ---------- Profile details ----------
  const detailsForm = qs('#profileDetailsForm');
  if (detailsForm) {
    const phoneInput = qs('#profile_phone');
    if (phoneInput) {
      phoneInput.addEventListener('input', () => {
        const digits = phoneInput.value.replace(/\D/g, '').slice(0, 10);
        const parts = [];
        if (digits.length > 0) parts.push('(' + digits.slice(0, Math.min(3, digits.length)) + (digits.length >= 3 ? ')' : ''));
        if (digits.length > 3) parts.push(' ' + digits.slice(3, Math.min(6, digits.length)));
        if (digits.length > 6) parts.push('-' + digits.slice(6));
        phoneInput.value = parts.join('');
      });
    }

    detailsForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const formData = new FormData(detailsForm);
      const { ok, data } = await request(urls.detailsUpdate, { method: 'POST', body: formData });
      if (!ok) {
        const errors = (data && data.errors) || {};
        const firstError = Object.values(errors)[0] || 'Unable to save profile.';
        showToast(firstError, true);
        return;
      }
      showToast('Profile details saved.');
    });
  }

  // ---------- Bio modal ----------
  const bioModal = qs('#bioModal');
  const bioForm = qs('#bioForm');
  const bioText = qs('#profileBioText');
  const bioTextarea = qs('#bioTextarea');
  const bioCounter = qs('#bioCharCounter');
  const maxBio = bioTextarea ? parseInt(bioTextarea.getAttribute('maxlength'), 10) || 600 : 600;

  const updateBioCounter = () => {
    if (!bioTextarea || !bioCounter) return;
    bioCounter.textContent = `${bioTextarea.value.length} / ${maxBio}`;
  };
  if (bioTextarea) {
    updateBioCounter();
    bioTextarea.addEventListener('input', updateBioCounter);
  }
  if (bioForm) {
    bioForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const formData = new FormData(bioForm);
      const { ok, data } = await request(urls.bioUpdate, { method: 'POST', body: formData });
      if (!ok) {
        showToast('Unable to update bio.', true);
        return;
      }
      if (bioText) {
        if (data.bio) {
          bioText.textContent = data.bio;
        } else {
          bioText.innerHTML = '<em>No bio yet.</em>';
        }
      }
      closeModal(bioModal);
      showToast('Bio updated.');
    });
  }

  // ---------- Experience ----------
  const experienceList = qs('#experienceList');
  const experienceForm = qs('#experienceForm');
  const experienceCount = () => qsa('.experience-item', experienceList || document).length;
  const experienceSummary = qs('.profile-esl-summary .summary-block:last-child p');

  const updateExperienceSummary = () => {
    if (!experienceSummary) return;
    const count = experienceCount();
    experienceSummary.textContent = count ? `${count} entries` : 'No experience added yet.';
  };
  updateExperienceSummary();

  const buildExperienceItem = (exp) => {
    const item = document.createElement('div');
    item.className = 'experience-item';
    item.dataset.experienceId = exp.id;
    const meta = document.createElement('div');
    meta.className = 'experience-meta';
    const start = exp.start_date ? new Date(exp.start_date) : null;
    const end = exp.end_date ? new Date(exp.end_date) : null;
    const startLabel = start ? start.toLocaleString('en-US', { month: 'short', year: 'numeric' }) : '';
    const endLabel = end ? end.toLocaleString('en-US', { month: 'short', year: 'numeric' }) : (exp.currently_work_here ? 'Present' : '');
    meta.textContent = `${exp.company} • ${startLabel}${endLabel ? '— ' + endLabel : ''}`;

    const main = document.createElement('div');
    main.className = 'experience-main';
    const title = document.createElement('div');
    title.className = 'experience-title';
    title.textContent = exp.job_title;
    main.appendChild(title);
    main.appendChild(meta);
    if (exp.description) {
      const desc = document.createElement('div');
      desc.className = 'experience-desc';
      desc.textContent = exp.description;
      main.appendChild(desc);
    }
    const del = document.createElement('button');
    del.type = 'button';
    del.className = 'icon-btn icon-btn--danger';
    del.setAttribute('data-experience-delete', exp.id);
    del.setAttribute('aria-label', 'Delete experience');
    del.textContent = '×';
    item.appendChild(main);
    item.appendChild(del);
    return item;
  };

  if (experienceForm) {
    experienceForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const formData = new FormData(experienceForm);
      const { ok, data } = await request(urls.experienceAdd, { method: 'POST', body: formData });
      if (!ok) {
        showToast('Unable to add experience.', true);
        return;
      }
      if (experienceList && data.experience) {
        if (qs('.experience-item', experienceList) || !experienceList.querySelector('.muted')) {
          experienceList.appendChild(buildExperienceItem(data.experience));
        } else {
          experienceList.innerHTML = '';
          experienceList.appendChild(buildExperienceItem(data.experience));
        }
        experienceForm.reset();
        updateExperienceSummary();
        showToast('Experience added.');
      }
    });
  }

  if (experienceList) {
    experienceList.addEventListener('click', async (e) => {
      const btn = e.target.closest('[data-experience-delete]');
      if (!btn) return;
      const experienceId = btn.getAttribute('data-experience-delete');
      const url = urls.experienceDeleteBase.replace('/0/', `/${experienceId}/`);
      const { ok } = await request(url, { method: 'POST' });
      if (!ok) {
        showToast('Unable to delete experience.', true);
        return;
      }
      const item = btn.closest('.experience-item');
      if (item) item.remove();
      if (!qs('.experience-item', experienceList)) {
        experienceList.innerHTML = '<p class="muted">No experience added yet.</p>';
      }
      updateExperienceSummary();
      showToast('Experience removed.');
    });
  }

  // ---------- Skills & Languages ----------
  const skillsPills = qs('#skillsPills');
  const languagesPills = qs('#languagesPills');
  const skillsPreview = qs('#profileSkillsPreview');
  const languagesPreview = qs('#profileLanguagesPreview');

  const renderPills = (container, items, type) => {
    if (!container) return;
    container.innerHTML = '';
    if (!items.length) {
      container.innerHTML = '<span class="muted">No ' + type + ' yet.</span>';
      return;
    }
    items.forEach((item) => {
      const pill = document.createElement('span');
      pill.className = 'pill-chip pill-chip--editable';
      pill.textContent = item.name;
      pill.dataset[`${type}Id`] = item.id;
      pill.dataset[`${type}Name`] = item.name;
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'pill-remove';
      remove.dataset[`${type}Remove`] = item.id;
      remove.setAttribute('aria-label', `Remove ${item.name}`);
      remove.textContent = '×';
      pill.appendChild(remove);
      container.appendChild(pill);
    });
  };

  const renderPreview = (container, items, type) => {
    if (!container) return;
    container.innerHTML = '';
    if (!items.length) {
      container.innerHTML = `<span class="muted">No ${type} yet.</span>`;
      return;
    }
    items.forEach((item) => {
      const pill = document.createElement('span');
      pill.className = 'pill-chip';
      pill.textContent = item.name;
      container.appendChild(pill);
    });
  };

  const currentItemsFromDom = (container, attr) => {
    if (!container) return [];
    return qsa(`[data-${attr}-id]`, container).map((el) => ({
      id: parseInt(el.getAttribute(`data-${attr}-id`), 10),
      name: el.getAttribute(`data-${attr}-name`) || el.textContent.replace('×', '').trim()
    }));
  };

  let skillItems = currentItemsFromDom(skillsPills, 'skill');
  let languageItems = currentItemsFromDom(languagesPills, 'language');

  const updateSkillsUI = (items) => {
    skillItems = items;
    renderPills(skillsPills, skillItems, 'skill');
    renderPreview(skillsPreview, skillItems, 'skills');
  };

  const updateLanguagesUI = (items) => {
    languageItems = items;
    renderPills(languagesPills, languageItems, 'language');
    renderPreview(languagesPreview, languageItems, 'languages');
  };

  const addSkill = async (name) => {
    const { ok, data } = await request(urls.skillAdd, {
      method: 'POST',
      body: new URLSearchParams({ skill: name }),
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest',
      },
    });
    if (!ok) {
      showToast((data.errors && data.errors.skill) || 'Unable to add skill.', true);
      return;
    }
    updateSkillsUI(data.skills || []);
  };

  const addLanguage = async (name) => {
    const { ok, data } = await request(urls.languageAdd, {
      method: 'POST',
      body: new URLSearchParams({ language: name }),
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest',
      },
    });
    if (!ok) {
      showToast((data.errors && data.errors.language) || 'Unable to add language.', true);
      return;
    }
    updateLanguagesUI(data.languages || []);
  };

  const bindPillHandlers = () => {
    if (skillsPills) {
      skillsPills.addEventListener('click', async (e) => {
        const btn = e.target.closest('[data-skill-remove]');
        if (!btn) return;
        const skillId = btn.getAttribute('data-skill-remove');
        const url = urls.skillDeleteBase.replace('/0/', `/${skillId}/`);
        const { ok, data } = await request(url, { method: 'POST' });
        if (!ok) {
          showToast('Unable to remove skill.', true);
          return;
        }
        updateSkillsUI(data.skills || []);
      });
    }
    if (languagesPills) {
      languagesPills.addEventListener('click', async (e) => {
        const btn = e.target.closest('[data-language-remove]');
        if (!btn) return;
        const languageId = btn.getAttribute('data-language-remove');
        const url = urls.languageDeleteBase.replace('/0/', `/${languageId}/`);
        const { ok, data } = await request(url, { method: 'POST' });
        if (!ok) {
          showToast('Unable to remove language.', true);
          return;
        }
        updateLanguagesUI(data.languages || []);
      });
    }
  };

  bindPillHandlers();

  const skillInput = qs('#skillInput');
  const skillAddBtn = qs('#skillAddBtn');
  if (skillInput && skillAddBtn) {
    const handle = () => {
      const value = skillInput.value.trim();
      if (!value) return;
      if (skillItems.some((s) => s.name.toLowerCase() === value.toLowerCase())) {
        showToast('Skill already added.', true);
        return;
      }
      addSkill(value);
      skillInput.value = '';
    };
    skillAddBtn.addEventListener('click', handle);
    skillInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handle();
      }
    });
  }

  const languageInput = qs('#languageInput');
  const languageAddBtn = qs('#languageAddBtn');
  if (languageInput && languageAddBtn) {
    const handle = () => {
      const value = languageInput.value.trim();
      if (!value) return;
      if (languageItems.some((l) => l.name.toLowerCase() === value.toLowerCase())) {
        showToast('Language already added.', true);
        return;
      }
      addLanguage(value);
      languageInput.value = '';
    };
    languageAddBtn.addEventListener('click', handle);
    languageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handle();
      }
    });
  }
})();
