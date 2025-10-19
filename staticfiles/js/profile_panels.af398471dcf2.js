/* =============================================================================
 * profile_panels.js
 * Slide-in editor logic for the Profile page (owner view).
 *
 * This file is tailored to your current HTML:
 *  - Edit buttons (openers by ID):
 *      #editSlideTrigger           → #slideEditor
 *      #editEmploymentTrigger      → #employmentSlideEditor
 *      #editEmergencyTrigger       → #emergencySlidePanel
 *      #editDemographicsTrigger    → #demographicsSlidePanel
 *      #editSkillsTrigger          → #skillsSlidePanel
 *
 *  - Forms inside panels (by ID or by panel selector):
 *      #personalSlideForm                  (Personal)
 *      #employmentSlideForm                (Employment)
 *      #emergencySlidePanel form           (Emergency — no form ID)
 *      #demographicsSlidePanel form        (Demographics — no form ID)
 *      #skillsSlideForm                    (Skills)
 *
 *  - Expected backend JSON shape on success:
 *      { ok: true, updated: { ...fields... } }
 *
 * UX Notes:
 *  - Adds/removes .open on panels and body.no-scroll to lock the page.
 *  - Shows a button spinner if your Save button contains:
 *        <span class="btn-text">Save</span><span class="spinner" style="display:none"></span>
 *  - If the response is NOT JSON/ok, falls back to full-page redirect (PRG safe).
 *
 * Accessibility:
 *  - Focuses the first control when a panel opens.
 *  - ESC closes any open panel.
 * ============================================================================= */

document.addEventListener('DOMContentLoaded', () => {
  // Mark as loaded so template fallback doesn't wire duplicate handlers
  try { window.__profilePanelsLoaded = true; } catch (e) {}
  /* ---------- Utilities ---------- */

  // Safe query helpers
  const qs  = (s, r=document) => r.querySelector(s);
  const qsa = (s, r=document) => Array.from(r.querySelectorAll(s));

  // CSRF cookie (Django standard)
  const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return decodeURIComponent(parts.pop().split(';').shift());
    return null;
  };
  const csrftoken = getCookie('csrftoken') || '';

  // Panel open/close
  function openPanel(selOrEl) {
    const panel = typeof selOrEl === 'string' ? qs(selOrEl) : selOrEl;
    if (!panel) return;
    panel.classList.add('open');                 // CSS also supports .visible, but we standardize on .open
    document.body.classList.add('no-scroll');    // prevent background scroll while open
    // Focus the first focusable control inside
    const first = panel.querySelector('input, select, textarea, button');
    if (first) first.focus({ preventScroll: true });
  }

  function closePanel(selOrEl) {
    const panel = typeof selOrEl === 'string' ? qs(selOrEl) : selOrEl;
    if (!panel) return;
    // Remove both classes to support legacy fallback that used .visible
    panel.classList.remove('open', 'visible');
    document.body.classList.remove('no-scroll');
  }

  // Expose for any legacy inline onclick="closePanel('...')"
  window.closePanel = (idOrSel) => closePanel(
    idOrSel.startsWith('#') ? idOrSel : `#${idOrSel}`
  );

  // Close on ESC
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') qsa('.slide-panel.open').forEach(closePanel);
  });

  // Wire simple openers by ID (your current HTML uses these)
  const openers = [
    ['#editSlideTrigger',        '#slideEditor'],
    ['#editEmploymentTrigger',   '#employmentSlideEditor'],
    ['#editEmergencyTrigger',    '#emergencySlidePanel'],
    ['#editDemographicsTrigger', '#demographicsSlidePanel'],
    ['#editSkillsTrigger',       '#skillsSlidePanel'],
  ];
  openers.forEach(([btnSel, panelSel]) => {
    const btn = qs(btnSel);
    if (btn) btn.addEventListener('click', (e) => { e.preventDefault(); openPanel(panelSel); });
  });

  /* ---------- Toggle groups in Employment (buttons set hidden input values) ---------- */
  // HTML pattern:
  // <div class="btn-toggle-group" data-name="authorized_us">
  //   <button type="button" data-value="yes">Yes</button>
  //   <button type="button" data-value="no">No</button>
  // </div>
  // <input type="hidden" name="authorized_us" value="{{ profile.work_in_us }}">
  qsa('.btn-toggle-group').forEach(group => {
    const fieldName = group.getAttribute('data-name'); // name of the hidden input to store selection
    if (!fieldName) return;
    // Find the sibling hidden input by name
    const hidden = group.parentElement.querySelector(`input[type="hidden"][name="${fieldName}"]`)
                 || group.querySelector(`input[type="hidden"][name="${fieldName}"]`);
    group.querySelectorAll('button[data-value]').forEach(btn => {
      btn.addEventListener('click', () => {
        // Visual "active" state
        group.querySelectorAll('button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        // Persist the value
        if (hidden) hidden.value = btn.getAttribute('data-value');
      });
    });
  });

  /* ---------- Generic AJAX submit handler for a form ---------- */
  async function submitPanelForm(form, { onSuccess } = {}) {
    // If the form has no action, abort
    if (!form || !form.action) return;

    // Button spinner UX (optional – only if present)
    const btn     = form.querySelector('button[type="submit"]');
    const spinner = btn ? btn.querySelector('.spinner') : null;
    const label   = btn ? btn.querySelector('.btn-text') : null;
    if (btn) btn.disabled = true;
    if (spinner && label) { spinner.style.display = 'inline-block'; label.style.display = 'none'; }

    try {
      const resp = await fetch(form.action, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrftoken, 'X-Requested-With': 'XMLHttpRequest' },
        body: new FormData(form),
      });

      // Try to parse JSON. If it fails, we’ll assume non-AJAX fallback (redirect).
      let data = {};
      try { data = await resp.json(); } catch (_) { data = {}; }

      // Not JSON or not ok → let server handle PRG; hard redirect to profile.
      if (!resp.ok || data.ok !== true) {
        window.location.href = '/profile/';     // PRG fallback keeps things consistent
        return;
      }

      // Patch page with returned fields
      if (typeof onSuccess === 'function') onSuccess(data.updated || {}, data);

      // Close panel if this form is inside one
      const panel = form.closest('.slide-panel');
      if (panel) closePanel(panel);

      // Toast if you have one
      if (typeof window.showToast === 'function') window.showToast('Saved');
    } catch (err) {
      alert('Network error. Please try again.');
    } finally {
      if (spinner && label) { spinner.style.display = 'none'; label.style.display = 'inline'; }
      if (btn) btn.disabled = false;
    }
  }

  /* ---------- Wire each form (matches your current HTML) ---------- */

  // PERSONAL (#personalSlideForm)
  (function wirePersonal() {
    const form = qs('#personalSlideForm');
    if (!form) return;

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      submitPanelForm(form, {
        onSuccess: (u) => {
          // Update full name display(s)
          qsa('[data-profile-full-name]').forEach(el => el.textContent = (u.full_name || '').trim());
          // Update labeled grid values
          const map = {
            'First Name:': u.firstname,
            'Last Name:':  u.lastname,
            'Email:':      u.personal_email,
            'Phone:':      u.phone_number,
            'Location:':   [u.city, u.state].filter(Boolean).join(', '),
          };
          qsa('.info-grid .info-item').forEach(item => {
            const label = item.querySelector('strong')?.textContent?.trim();
            const span  = item.querySelector('span');
            if (label && span && (label in map)) span.textContent = map[label] || '';
          });
        }
      });
    });
  })();

  // EMPLOYMENT (#employmentSlideForm)
  (function wireEmployment() {
    const form = qs('#employmentSlideForm');
    if (!form) return;

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      submitPanelForm(form, {
        onSuccess: (u) => {
          const map = {
            'Work in US:':         u.work_in_us,
            'Sponsorship Needed:': u.sponsorship_needed,
            'Disability:':         u.disability,
            'LGBTQ+:':             u.lgbtq,
            'Gender:':             u.gender,
            'Veteran:':            u.veteran_status,
          };
          qsa('.info-grid .info-item').forEach(item => {
            const label = item.querySelector('strong')?.textContent?.trim();
            const span  = item.querySelector('span');
            if (label && span && (label in map)) span.textContent = map[label] || '';
          });
        }
      });
    });
  })();

  // EMERGENCY (#emergencySlidePanel form) — no form ID in your HTML, target first form inside the panel
  (function wireEmergency() {
    const form = qs('#emergencySlidePanel form');
    if (!form) return;

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      submitPanelForm(form, {
        onSuccess: (u) => {
          const map = {
            'First Name:':   u.emergency_contact_firstname,
            'Last Name:':    u.emergency_contact_lastname,
            'Relationship:': u.emergency_contact_relationship,
            'Phone:':        u.emergency_contact_phone,
            'Email:':        u.emergency_contact_email,
          };
          qsa('.info-grid .info-item').forEach(item => {
            const label = item.querySelector('strong')?.textContent?.trim();
            const span  = item.querySelector('span');
            if (label && span && (label in map)) span.textContent = map[label] || '';
          });
        }
      });
    });
  })();

  // DEMOGRAPHICS (#demographicsSlidePanel form) — no form ID in your HTML, target first form inside the panel
  (function wireDemographics() {
    const form = qs('#demographicsSlidePanel form');
    if (!form) return;

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      submitPanelForm(form, {
        onSuccess: (u) => {
          const map = {
            'Gender:':                 u.gender,
            'Ethnicity:':              u.ethnicity,
            'Veteran Status:':         u.veteran_status,
            'Disability Explanation:': u.disability_explanation,
            'Veteran Explanation:':    u.veteran_explanation,
          };
          qsa('.info-grid .info-item').forEach(item => {
            const label = item.querySelector('strong')?.textContent?.trim();
            const span  = item.querySelector('span');
            if (label && span && (label in map)) span.textContent = map[label] || '';
          });
        }
      });
    });
  })();

  /* ---------- SKILLS (#skillsSlideForm) — render + submit ---------- */
  (function wireSkills() {
    const form         = qs('#skillsSlideForm');
    const dataNode     = qs('#skillData'); // <script type="application/json" id="skillData">…</script>
    const selectedWrap = qs('#selectedSkills');
    const suggestedWrap= qs('#suggestedSkillsContainer');
    const input        = qs('#skillInput');
    const addHidden    = qs('#addSkillsInput');
    const removeHidden = qs('#removeSkillsInput');
    const refreshBtn   = qs('#refreshSuggestionsBtn');
    const dropdown     = qs('#suggestions');

    if (!form || !dataNode || !selectedWrap || !input || !addHidden || !removeHidden) return;

    /* ---------------- State ---------------- */
    const parsed = safeParseJSON(dataNode.textContent);
    // Accept either: {"selected":[...], "suggested":[...]} OR ["a","b",...]
    const initialSelected  = Array.isArray(parsed) ? parsed : (parsed?.selected || []);
    const initialSuggested = Array.isArray(parsed) ? []     : (parsed?.suggested || []);

    const norm             = (s) => (s || '').trim();
    const selected         = new Set(initialSelected.map(norm));
    const addedThisSession = new Set();
    const removedThisSession = new Set();
    const initialSet       = new Set(initialSelected.map(s => s.toLowerCase()));

    // master suggestion pool (server + safe fallback)
    const masterSuggestionPool = Array.from(new Set(
      (initialSuggested || [])
        .concat(initialSelected || [])
        .concat([
          'Leadership','Time Management','Excel','Word','PowerPoint','Python',
          'JavaScript','Teamwork','Communication','Problem Solving'
        ])
    ));

    /* ---------------- Render helpers ---------------- */
    function chip(text) {
      const pill = document.createElement('span');
      pill.className = 'skill-tag';
      pill.textContent = text;

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.setAttribute('aria-label', `Remove ${text}`);
      btn.textContent = '×';
      btn.addEventListener('click', () => removeSkill(text));

      pill.appendChild(btn);
      return pill;
    }

    function renderSelected() {
      selectedWrap.innerHTML = '';
      if (selected.size === 0) {
        selectedWrap.innerHTML = '<em>No skills selected yet.</em>';
        return;
      }
      selected.forEach(skill => selectedWrap.appendChild(chip(skill)));
    }

    function renderSuggested(list) {
      if (!suggestedWrap) return;
      suggestedWrap.innerHTML = '';
      (list || []).forEach(s => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'suggested-skill-btn';
        btn.textContent = s;
        btn.addEventListener('click', () => addSkill(s));
        suggestedWrap.appendChild(btn);
      });
    }

    function syncHidden() {
      addHidden.value = JSON.stringify(Array.from(addedThisSession));
      removeHidden.value = JSON.stringify(Array.from(removedThisSession));
    }

    /* ---------------- Mutators ---------------- */
    function addSkill(raw) {
      const s = norm(raw);
      if (!s) return;

      // If user re-adds something they marked for removal, unmark it
      if (removedThisSession.has(s)) removedThisSession.delete(s);

      // Only mark as added if it wasn’t part of initial selection
      if (!initialSet.has(s.toLowerCase())) addedThisSession.add(s);

      selected.add(s);
      renderSelected();
      syncHidden();
      hideDropdown();
    }

    function removeSkill(raw) {
      const s = norm(raw);
      if (!s) return;

      selected.delete(s);

      // If it was newly added this session, cancel that addition…
      if (addedThisSession.has(s)) {
        addedThisSession.delete(s);
      } else if (initialSet.has(s.toLowerCase())) {
        // …otherwise, it existed initially → mark as removed
        removedThisSession.add(s);
      }

      renderSelected();
      syncHidden();
    }

    /* ---------------- Typeahead ---------------- */
    function filterSuggestions(q) {
      const query = norm(q).toLowerCase();
      if (!query) return [];
      return masterSuggestionPool
        .filter(s => s.toLowerCase().includes(query))
        .filter(s => !selected.has(norm(s)))
        .slice(0, 6);
    }

    function showDropdown(items) {
      if (!dropdown) return;
      dropdown.innerHTML = '';
      if (!items.length) { dropdown.style.display = 'none'; return; }
      items.forEach(it => {
        const div = document.createElement('div');
        div.className = 'dropdown-item';
        div.textContent = it;
        div.addEventListener('click', () => { addSkill(it); input.value=''; });
        dropdown.appendChild(div);
      });
      dropdown.style.display = 'block';
    }

    function hideDropdown() {
      if (dropdown) dropdown.style.display = 'none';
    }

    /* ---------------- Events ---------------- */
    input.addEventListener('input', () => {
      const items = filterSuggestions(input.value);
      showDropdown(items);
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const val = norm(input.value);
        if (val) addSkill(val);
        input.value = '';
      }
    });

    document.addEventListener('click', (e) => {
      if (!dropdown) return;
      if (!dropdown.contains(e.target) && e.target !== input) hideDropdown();
    });

    if (refreshBtn && suggestedWrap) {
      refreshBtn.addEventListener('click', () => {
        // simple re-shuffle for now (replace with server fetch if needed)
        const shuffled = masterSuggestionPool
          .filter(s => !selected.has(norm(s)))
          .sort(() => Math.random() - 0.5)
          .slice(0, 10);
        renderSuggested(shuffled);
      });
    }

    /* ---------------- Submit (keeps your existing AJAX behavior) ---------------- */
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      submitPanelForm(form, {
        onSuccess: (u) => {
          // Update on-page Skills list if backend returns skills array
          if (Array.isArray(u.skills)) {
            let ul = qs('.skill-list');
            if (!ul) {
              // Create the list in the Skills section if it doesn't exist yet
              const section = (function findSkillsSection(){
                return qsa('.section').find(sec => (sec.querySelector('.section-title')?.textContent || '').trim().toLowerCase() === 'skills');
              })();
              if (section) {
                // Remove placeholder paragraph if present
                const ph = section.querySelector('p');
                if (ph) ph.remove();
                ul = document.createElement('ul');
                ul.className = 'skill-list';
                section.appendChild(ul);
              }
            }
            if (ul) {
              ul.innerHTML = u.skills.map(s => `<li class="skill-item">${s}</li>`).join('');
            }
          }
          // Reset session diff after successful save
          addedThisSession.clear();
          removedThisSession.clear();
          syncHidden();
        }
      });
    });

    /* ---------------- Boot ---------------- */
    renderSelected();
    renderSuggested(initialSuggested);

    /* ---------------- Utils ---------------- */
    function safeParseJSON(txt) { try { return JSON.parse(txt || ''); } catch { return null; } }
  })();


  /* ---------- Bio toggles (your template calls these) ---------- */

  // Show/hide truncated vs full bio text
  window.toggleBio = function toggleBio() {
    const short = qs('#bioPreview');
    const full  = qs('#fullBio');
    if (!short || !full) return;
    const showingFull = full.style.display === 'block';
    full.style.display  = showingFull ? 'none'  : 'block';
    short.style.display = showingFull ? 'block' : 'none';
  };

  // Show/hide the Bio edit form
  window.toggleBioEdit = function toggleBioEdit() {
    const form  = qs('#editBioForm');
    const short = qs('#bioPreview');
    const full  = qs('#fullBio');
    if (!form) return;
    const showing = form.style.display === 'block';
    form.style.display  = showing ? 'none' : 'block';
    // Hide the previews when editing; restore short preview when closing
    if (!showing) { if (short) short.style.display = 'none'; if (full) full.style.display = 'none'; }
    else          { if (short) short.style.display = 'block'; }
  };
});
