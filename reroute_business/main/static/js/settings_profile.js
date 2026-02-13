(function () {
  const form = document.getElementById('profileEditForm');
  if (!form) return;

  const coreInput = document.getElementById('coreSkillsInput');
  const softInput = document.getElementById('softSkillsInput');
  const experiencesInput = document.getElementById('experiencesInput');
  const certsInput = document.getElementById('certificationsInput');

  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const setHidden = (input, value) => {
    if (!input) return;
    input.value = JSON.stringify(value);
  };

  const buildChip = (label) => {
    const chip = document.createElement('span');
    chip.className = 'pill-chip pill-chip--editable';
    chip.dataset.value = label;
    chip.textContent = label;
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'pill-remove';
    remove.setAttribute('aria-label', `Remove ${label}`);
    remove.textContent = '×';
    remove.addEventListener('click', () => {
      chip.remove();
      syncSkills();
    });
    chip.appendChild(remove);
    return chip;
  };

  const readChips = (list) => {
    return qsa('.pill-chip', list)
      .map((chip) => (chip.dataset.value || chip.textContent || '').replace('×', '').trim())
      .filter(Boolean);
  };

  const syncSkills = () => {
    const coreSection = qs('[data-skill-section="core"]', form);
    const softSection = qs('[data-skill-section="soft"]', form);
    if (coreSection) {
      const list = qs('[data-skill-list]', coreSection);
      setHidden(coreInput, readChips(list));
    }
    if (softSection) {
      const list = qs('[data-skill-list]', softSection);
      setHidden(softInput, readChips(list));
    }
  };

  const initSkillSection = (section) => {
    if (!section) return;
    const list = qs('[data-skill-list]', section);
    const input = qs('[data-skill-input]', section);
    const addBtn = qs('[data-skill-add]', section);

    qsa('.pill-chip', list).forEach((chip) => {
      if (!chip.dataset.value) {
        chip.dataset.value = chip.childNodes[0]?.textContent?.trim() || chip.textContent.replace('×', '').trim();
      }
      const removeBtn = qs('.pill-remove', chip);
      if (removeBtn) {
        removeBtn.addEventListener('click', () => {
          chip.remove();
          syncSkills();
        });
      }
    });

    const addChip = () => {
      const value = (input.value || '').trim();
      if (!value) return;
      const existing = readChips(list).map((v) => v.toLowerCase());
      if (existing.includes(value.toLowerCase())) {
        input.value = '';
        return;
      }
      const placeholder = qs('.muted', list);
      if (placeholder) placeholder.remove();
      list.appendChild(buildChip(value));
      input.value = '';
      syncSkills();
    };

    addBtn?.addEventListener('click', addChip);
    input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        addChip();
      }
    });
  };

  initSkillSection(qs('[data-skill-section="core"]', form));
  initSkillSection(qs('[data-skill-section="soft"]', form));
  syncSkills();

  // Profile photo preview (visual only until Save Profile is submitted)
  const photoInput = document.getElementById('profile_photo');
  const photoShell = qs('.profile-photo-shell', form);
  if (photoInput && photoShell) {
    photoInput.addEventListener('change', () => {
      const file = photoInput.files && photoInput.files[0];
      if (!file) return;
      if (!file.type.startsWith('image/')) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        let img = qs('img', photoShell);
        if (!img) {
          img = document.createElement('img');
          img.alt = 'Profile photo preview';
          photoShell.prepend(img);
        }
        img.src = String(event.target?.result || '');
        const initials = qs('.profile-photo-initials', photoShell);
        if (initials) initials.style.display = 'none';
      };
      reader.readAsDataURL(file);
    });
  }

  // Experience editor
  const experienceList = qs('[data-experience-list]', form);
  const addExperienceBtn = qs('[data-add-experience]', form);
  const experienceTemplate = document.getElementById('experienceTemplate');
  const highlightTemplate = document.getElementById('highlightTemplate');

  const wireHighlightRow = (row) => {
    const removeBtn = qs('[data-remove-highlight]', row);
    removeBtn?.addEventListener('click', () => row.remove());
  };

  const addHighlight = (container) => {
    if (!highlightTemplate) return;
    const node = highlightTemplate.content.firstElementChild.cloneNode(true);
    wireHighlightRow(node);
    container.appendChild(node);
  };

  const wireExperienceBlock = (block) => {
    const removeBtn = qs('[data-remove-experience]', block);
    const highlightList = qs('[data-highlights]', block);
    const addHighlightBtn = qs('[data-add-highlight]', block);

    removeBtn?.addEventListener('click', () => block.remove());
    addHighlightBtn?.addEventListener('click', () => addHighlight(highlightList));

    qsa('[data-highlight]', block).forEach(wireHighlightRow);
  };

  if (experienceList) {
    qsa('[data-experience]', experienceList).forEach(wireExperienceBlock);
  }

  addExperienceBtn?.addEventListener('click', () => {
    if (!experienceTemplate || !experienceList) return;
    const placeholder = qs('.muted', experienceList);
    if (placeholder) placeholder.remove();
    const node = experienceTemplate.content.firstElementChild.cloneNode(true);
    const highlights = qs('[data-highlights]', node);
    if (highlights) addHighlight(highlights);
    wireExperienceBlock(node);
    experienceList.appendChild(node);
  });

  // Certifications editor
  const certList = qs('[data-cert-list]', form);
  const addCertBtn = qs('[data-add-cert]', form);
  const certTemplate = document.getElementById('certTemplate');

  const wireCertRow = (row) => {
    const removeBtn = qs('[data-remove-cert]', row);
    removeBtn?.addEventListener('click', () => row.remove());
  };

  if (certList) {
    qsa('[data-cert]', certList).forEach(wireCertRow);
  }

  addCertBtn?.addEventListener('click', () => {
    if (!certTemplate || !certList) return;
    const placeholder = qs('.muted', certList);
    if (placeholder) placeholder.remove();
    const node = certTemplate.content.firstElementChild.cloneNode(true);
    wireCertRow(node);
    certList.appendChild(node);
  });

  const collectExperiences = () => {
    const items = [];
    if (!experienceList) return items;
    qsa('[data-experience]', experienceList).forEach((block) => {
      const title = (qs('[data-exp-title]', block)?.value || '').trim();
      const company = (qs('[data-exp-company]', block)?.value || '').trim();
      const startYear = (qs('[data-exp-start-year]', block)?.value || '').trim();
      const endYear = (qs('[data-exp-end-year]', block)?.value || '').trim();
      const highlights = qsa('[data-highlight-input]', block)
        .map((input) => (input.value || '').trim())
        .filter(Boolean);
      if (!title && !company && !startYear && !endYear && highlights.length === 0) return;
      items.push({
        title,
        company,
        start_year: startYear,
        end_year: endYear,
        highlights,
      });
    });
    return items;
  };

  const collectCerts = () => {
    const items = [];
    if (!certList) return items;
    qsa('[data-cert]', certList).forEach((row) => {
      const title = (qs('[data-cert-title]', row)?.value || '').trim();
      const issuer = (qs('[data-cert-issuer]', row)?.value || '').trim();
      const year = (qs('[data-cert-year]', row)?.value || '').trim();
      if (!title) return;
      items.push({ title, issuer, year });
    });
    return items;
  };

  form.addEventListener('submit', () => {
    setHidden(experiencesInput, collectExperiences());
    setHidden(certsInput, collectCerts());
    syncSkills();
    const saveBtn = qs('[data-save-profile]', form);
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.classList.add('is-loading');
    }
  });
})();
