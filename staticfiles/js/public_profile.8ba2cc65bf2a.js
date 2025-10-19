/* =============================================================
   ReRoute — Public Profile JS (Improved)
   Date: Aug 11, 2025
   What’s new:
   - Robust CSRF for Django AJAX (POST)
   - SlidePanel helper (open/close, ESC + click-outside, body scroll lock)
   - Accessible tabs + suggestions (ARIA roles)
   - Safer DOM ops (no innerHTML for user data)
   - Debounced search, better error handling, DRY helpers
   - Initializes toggle buttons from saved values
   - Closes suggestions on outside click / ESC
   -------------------------------------------------------------
   Drop-in: Replace your existing public_profile.js with this file.
   Make sure your HTML IDs match those used below (same as your file).
   ============================================================= */

(function () {
  'use strict';

  // ----------------------------
  // Tiny DOM + CSRF utilities
  // ----------------------------
  const qs = (sel, el = document) => el.querySelector(sel);
  const qsa = (sel, el = document) => Array.from(el.querySelectorAll(sel));
  const on = (el, evt, cb, opt) => el && el.addEventListener(evt, cb, opt);

  function getCookie(name) {
    // Standard Django cookie parser
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
  }
  const CSRF = () => getCookie('csrftoken');

  // Debounce helper for input events
  function debounce(fn, wait = 200) {
    let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn.apply(null, args), wait); };
  }

  // Central registry for open panels (ensures only one open at a time)
  const OpenPanels = new Set();

  // ------------------------------------
  // SlidePanel: open/close + accessibility
  // ------------------------------------
  class SlidePanel {
    /**
     * @param {Object} cfg
     * @param {string} cfg.triggerId - Button that opens the panel
     * @param {string} cfg.panelId - Panel element id
     * @param {string} cfg.cancelId - Button that closes the panel
     * @param {string} cfg.formId - Form inside the panel
     * @param {string} cfg.saveBtnId - Save button id (spinner/text children optional)
     */
    constructor(cfg) {
      this.trigger = qs('#' + cfg.triggerId);
      this.panel = qs('#' + cfg.panelId);
      this.cancelBtn = qs('#' + cfg.cancelId);
      this.form = qs('#' + cfg.formId);
      this.saveBtn = qs('#' + cfg.saveBtnId);
      this.btnText = this.saveBtn ? this.saveBtn.querySelector('.btn-text') : null;
      this.spinner = this.saveBtn ? this.saveBtn.querySelector('.spinner') : null;

      // Set ARIA attributes for better a11y (if markup allows)
      if (this.panel) {
        this.panel.setAttribute('role', 'dialog');
        this.panel.setAttribute('aria-modal', 'true');
        this.panel.setAttribute('aria-hidden', 'true');
      }

      this.bind();
    }

    bind() {
      on(this.trigger, 'click', () => this.open());
      on(this.cancelBtn, 'click', () => this.close());

      // Close on ESC and click-outside
      on(document, 'keydown', (e) => {
        if (e.key === 'Escape' && this.isOpen()) this.close();
      });
      on(document, 'click', (e) => {
        if (!this.isOpen()) return;
        if (this.panel && !this.panel.contains(e.target) && e.target !== this.trigger) this.close();
      });

      // AJAX form submit with CSRF
      if (this.form) {
        on(this.form, 'submit', (e) => {
          e.preventDefault();
          this.toggleSaving(true);

          fetch(this.form.action, {
            method: 'POST',
            headers: {
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': CSRF() || '',
            },
            credentials: 'same-origin',
            body: new FormData(this.form),
          })
            .then(async (res) => {
              // Handle non-200s gracefully
              if (!res.ok) {
                const text = await res.text().catch(() => '');
                throw new Error(text || `Request failed (${res.status})`);
              }
              return res.json().catch(() => ({}));
            })
            .then((data) => {
              if (data && data.success) {
                this.close();
                // Be pragmatic: reload so server is truthy.
                // Swap to in-place DOM updates later if needed.
                window.location.reload();
              } else {
                alert('❌ Failed to save. Please try again.');
              }
            })
            .catch((err) => {
              console.error(err);
              alert('❌ Server error while saving.');
            })
            .finally(() => this.toggleSaving(false));
        });
      }
    }

    isOpen() { return this.panel && this.panel.classList.contains('visible'); }

    open() {
      // Close other panels
      OpenPanels.forEach((p) => p !== this && p.close());
      OpenPanels.add(this);

      if (!this.panel) return;
      this.panel.classList.add('visible');
      this.panel.style.right = '0';
      this.panel.setAttribute('aria-hidden', 'false');
      document.body.classList.add('no-scroll');

      // Focus first focusable element for accessibility
      const firstFocusable = this.panel.querySelector('input, select, textarea, button, [tabindex]');
      if (firstFocusable) firstFocusable.focus({ preventScroll: true });
    }

    close() {
      if (!this.panel) return;
      this.panel.classList.remove('visible');
      this.panel.style.right = '-100%';
      this.panel.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('no-scroll');
      OpenPanels.delete(this);
    }

    toggleSaving(isSaving) {
      if (this.spinner) this.spinner.style.display = isSaving ? 'inline-block' : 'none';
      if (this.btnText) this.btnText.style.display = isSaving ? 'none' : 'inline';
      if (this.saveBtn) this.saveBtn.disabled = !!isSaving;
    }
  }

  // ----------------------------
  // Init on DOMContentLoaded
  // ----------------------------
  document.addEventListener('DOMContentLoaded', () => {
    // ===== Tabs =====
    const tabButtons = qsa('.tab-button');
    const tabSections = qsa('.tab-section');

    // Add basic ARIA semantics if not present
    const tablist = qs('[data-role="tablist"]') || qs('.tab-container');
    if (tablist) tablist.setAttribute('role', 'tablist');

    tabButtons.forEach((btn) => {
      btn.setAttribute('role', 'tab');
      on(btn, 'click', () => {
        tabSections.forEach((s) => { s.style.display = 'none'; s.setAttribute('aria-hidden', 'true'); });
        tabButtons.forEach((b) => { b.classList.remove('active-tab'); b.setAttribute('aria-selected', 'false'); });

        const section = qs('#' + btn.dataset.target);
        if (section) {
          section.style.display = 'block';
          section.setAttribute('aria-hidden', 'false');
          btn.classList.add('active-tab');
          btn.setAttribute('aria-selected', 'true');
        }
      });
    });

    // ===== Slide Panels =====
    [
      { triggerId: 'editSlideTrigger', panelId: 'slideEditor', cancelId: 'cancelSlide', formId: 'personalSlideForm', saveBtnId: 'saveSlide' },
      { triggerId: 'editEmploymentTrigger', panelId: 'employmentSlideEditor', cancelId: 'cancelEmploymentSlide', formId: 'employmentSlideForm', saveBtnId: 'saveEmploymentSlide' },
      { triggerId: 'editSkillsTrigger', panelId: 'skillsSlidePanel', cancelId: 'cancelSkillsSlide', formId: 'skillsSlideForm', saveBtnId: 'saveSkillsSlide' },
      { triggerId: 'editEmergencyTrigger', panelId: 'emergencySlidePanel', cancelId: 'cancelEmergencySlide', formId: 'emergencySlideForm', saveBtnId: 'saveEmergencySlide' },
      { triggerId: 'editDemographicsTrigger', panelId: 'demographicsSlidePanel', cancelId: 'cancelDemographicsSlide', formId: 'demographicsSlideForm', saveBtnId: 'saveDemographicsSlide' },
    ].forEach(cfg => new SlidePanel(cfg));

    // ===== Skills UI =====
    const skillInput = qs('#skillInput');
    const selectedSkillsDiv = qs('#selectedSkills');
    const addSkillsInput = qs('#addSkillsInput');
    const removeSkillsInput = qs('#removeSkillsInput');
    const suggestionsDiv = qs('#suggestions');
    const suggestedContainer = qs('#suggestedSkillsContainer');
    const refreshBtn = qs('#refreshSuggestionsBtn');

    const selectedSkills = new Map(); // key: lowercase, value: original case
    const removedSkills = new Set();
    let allSkills = [];

    // Preload existing skills from <script id="skillData" type="application/json">["...", ...]</script>
    const skillData = qs('#skillData');
    if (skillData) {
      try {
        const initialSkills = JSON.parse(skillData.textContent || '[]');
        initialSkills.forEach((sk) => {
          const lower = String(sk).toLowerCase();
          if (!selectedSkills.has(lower)) selectedSkills.set(lower, String(sk));
        });
        renderChips();
        updateHiddenInputs();
      } catch (e) {
        console.error('Failed to parse skillData JSON', e);
      }
    }

    function updateHiddenInputs() {
      // Server splits by comma and trims; keep it lean without trailing spaces
      if (addSkillsInput) addSkillsInput.value = Array.from(selectedSkills.values()).join(',');
      if (removeSkillsInput) removeSkillsInput.value = Array.from(removedSkills).join(',');
    }

    function renderChips() {
      if (!selectedSkillsDiv) return;
      selectedSkillsDiv.innerHTML = '';
      selectedSkills.forEach((original, lower) => {
        const chip = document.createElement('div');
        chip.className = 'chip';

        const text = document.createElement('span');
        text.className = 'chip-text';
        text.textContent = original; // ✅ safe textContent

        const x = document.createElement('button');
        x.type = 'button';
        x.className = 'remove-btn';
        x.setAttribute('aria-label', `Remove ${original}`);
        x.dataset.skill = lower;
        x.textContent = '×';
        on(x, 'click', () => {
          removedSkills.add(lower);
          selectedSkills.delete(lower);
          renderChips();
          updateHiddenInputs();
          // keep suggestions coherent
          if (suggestionsDiv) suggestionsDiv.style.display = 'none';
        });

        chip.appendChild(text);
        chip.appendChild(x);
        selectedSkillsDiv.appendChild(chip);
      });
    }

    function filterSuggestions(text) {
      if (!suggestionsDiv) return;
      suggestionsDiv.innerHTML = '';
      if (!text) return (suggestionsDiv.style.display = 'none');

      const q = text.toLowerCase();
      const filtered = allSkills.filter((s) => s.toLowerCase().includes(q) && !selectedSkills.has(s.toLowerCase()));
      if (filtered.length === 0) return (suggestionsDiv.style.display = 'none');

      // ARIA listbox for suggestions
      suggestionsDiv.setAttribute('role', 'listbox');

      filtered.slice(0, 10).forEach((skill) => {
        const opt = document.createElement('div');
        opt.setAttribute('role', 'option');
        opt.tabIndex = 0;
        opt.textContent = skill;
        on(opt, 'click', () => addSkill(skill));
        on(opt, 'keydown', (e) => { if (e.key === 'Enter') addSkill(skill); });
        suggestionsDiv.appendChild(opt);
      });

      suggestionsDiv.style.display = 'block';
    }

    const debouncedSuggest = debounce((val) => filterSuggestions(val), 180);

    function addSkill(skill) {
      const lower = skill.toLowerCase();
      if (!selectedSkills.has(lower)) {
        selectedSkills.set(lower, skill);
        removedSkills.delete(lower);
        if (skillInput) skillInput.value = '';
        renderChips();
        updateHiddenInputs();
        if (suggestionsDiv) suggestionsDiv.style.display = 'none';
      }
    }

    on(skillInput, 'input', (e) => debouncedSuggest(e.target.value));

    on(skillInput, 'keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const val = (skillInput.value || '').trim();
        if (val) addSkill(val);
      } else if (e.key === 'Escape') {
        if (suggestionsDiv) suggestionsDiv.style.display = 'none';
      }
    });

    // Close suggestions if clicking anywhere else
    on(document, 'click', (e) => {
      if (!suggestionsDiv || !skillInput) return;
      if (!suggestionsDiv.contains(e.target) && e.target !== skillInput) {
        suggestionsDiv.style.display = 'none';
      }
    });

    // Load predefined skills from backend (expects JSON array of strings)
    function loadSuggestedSkills() {
      if (!suggestedContainer) return;
      suggestedContainer.innerHTML = '';

      fetch('/api/skills/', { credentials: 'same-origin' })
        .then(async (res) => {
          if (!res.ok) throw new Error(`GET /api/skills/ failed (${res.status})`);
          const data = await res.json();
          // Normalize: accept ["Skill"] or [{name:"Skill"}]
          allSkills = Array.isArray(data)
            ? data.map((d) => (typeof d === 'string' ? d : (d && d.name) || '')).filter(Boolean)
            : [];

          // Remove already selected
          const pool = allSkills.filter((s) => !selectedSkills.has(s.toLowerCase()));
          // Shuffle a copy (Fisher–Yates)
          for (let i = pool.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [pool[i], pool[j]] = [pool[j], pool[i]];
          }
          const top = pool.slice(0, 9);

          top.forEach((skill) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'suggested-skill-btn';
            btn.textContent = skill;
            on(btn, 'click', () => { addSkill(skill); btn.remove(); });
            suggestedContainer.appendChild(btn);
          });
        })
        .catch((err) => {
          console.warn('Skill suggestions unavailable:', err);
        });
    }

    loadSuggestedSkills();
    on(refreshBtn, 'click', loadSuggestedSkills);

    // ===== Toggle groups (init from saved values) =====
    qsa('.btn-toggle-group').forEach((group) => {
      const input = group.nextElementSibling; // hidden input with the value
      if (!input) return;

      // Initialize active state from current value
      const current = (input.value || '').toLowerCase();
      qsa('button', group).forEach((btn) => {
        const val = (btn.dataset.value || '').toLowerCase();
        if (val && val === current) btn.classList.add('active');
        on(btn, 'click', () => {
          qsa('button', group).forEach((b) => b.classList.remove('active'));
          btn.classList.add('active');
          input.value = btn.dataset.value || '';
        });
      });
    });

    // ===== Phone number formatting (lightweight) =====
    const formatPhone = (input) => {
      // Preserve digits and apply 3-3-4 mask; defer complex caret mgmt for now
      const digits = (input.value || '').replace(/\D/g, '').slice(0, 10);
      const parts = [];
      if (digits.length > 0) parts.push(digits.slice(0, 3));
      if (digits.length > 3) parts.push(digits.slice(3, 6));
      if (digits.length > 6) parts.push(digits.slice(6, 10));
      input.value = parts.join('-');
    };

    on(qs('#phone_number'), 'input', (e) => formatPhone(e.target));
    on(qs('#emergency_contact_phone'), 'input', (e) => formatPhone(e.target));
  });
})();
