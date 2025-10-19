// resumes/js/skills_step.js
// PURPOSE: Power the Skills step UI with zero backend calls.
// CONTRACTS WITH TEMPLATE:
//   - Hidden <textarea id="skills_input" name="selected_skills"> contains CSV
//   - Suggested tags are buttons with class "skill-tag" and data-skill="..."
//   - Visual list of selected chips renders inside #selectedSkillsDisplay
//
// DESIGN CHOICES:
//   - Normalize skills to lowercase to avoid dupes like "Forklift" vs "forklift"
//   - Max 10 skills (easy to change)
//   - Clicking a selected chip removes it
//   - Buttons reflect selected state (active class)

document.addEventListener('DOMContentLoaded', () => {
  // --- DOM lookups
  const hiddenCSV   = document.getElementById('skills_input');               // hidden CSV field
  const selectedBox = document.getElementById('selectedSkillsDisplay');      // visual chips container
  const tagsWrap    = document.getElementById('skillTagContainer');          // suggested tags parent
  const customInput = document.getElementById('customSkillInput');           // free-entry input
  const form = document.getElementById('skillsForm');

  if (!hiddenCSV || !selectedBox) return; // nothing to do

  // --- helpers
  const norm = s => (s || '').trim().toLowerCase();
  const fromCSV = csv => (csv || '').split(',').map(norm).filter(Boolean);
  const toCSV   = arr => [...new Set(arr.map(norm))].filter(Boolean).join(',');

  const MAX_SKILLS = 10;

  // --- state (hydrate from server-provided CSV)
  const selected = new Set(fromCSV(hiddenCSV.value));

  // --- render the selected chips + sync hidden CSV
  function renderSelected() {
    selectedBox.innerHTML = '';
    if (selected.size === 0) {
      const none = document.createElement('span');
      none.className = 'text-muted';
      none.textContent = 'None';
      selectedBox.appendChild(none);
    } else {
      [...selected].forEach(skill => {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'selected-skill-tag';
        chip.dataset.skill = skill;
        chip.title = 'Click to remove';
        chip.innerHTML = `${skill} <span class="remove-skill" aria-hidden="true">✕</span>`;
        chip.addEventListener('click', () => {
          selected.delete(skill);
          sync();
        });
        selectedBox.appendChild(chip);
      });
    }
    hiddenCSV.value = toCSV([...selected]);
  }

  // --- reflect selected state on suggested buttons
  function markSuggested() {
    if (!tagsWrap) return;
    tagsWrap.querySelectorAll('.skill-tag[data-skill]').forEach(btn => {
      const key = norm(btn.dataset.skill || btn.textContent);
      btn.classList.toggle('active', selected.has(key));
      // Optional: hard cap behavior (disable unselected when at cap)
      btn.disabled = selected.size >= MAX_SKILLS && !selected.has(key);
    });
  }

  function sync() {
    renderSelected();
    markSuggested();
  }

  // --- click to toggle suggested tags
  if (tagsWrap) {
    tagsWrap.addEventListener('click', (e) => {
      const btn = e.target.closest('.skill-tag[data-skill]');
      if (!btn) return;
      const key = norm(btn.dataset.skill || btn.textContent);
      if (!key) return;

      if (selected.has(key)) {
        selected.delete(key);
      } else {
        if (selected.size >= MAX_SKILLS) {
          alert(`You can only select up to ${MAX_SKILLS} skills.`);
          return;
        }
        selected.add(key);
      }
      sync();
    });
  }

  // --- free entry on Enter
  if (customInput) {
    customInput.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      const key = norm(customInput.value);
      if (!key) return;
      if (selected.has(key)) {
        alert('This skill is already added.');
      } else if (selected.size >= MAX_SKILLS) {
        alert(`You can only select up to ${MAX_SKILLS} skills.`);
      } else {
        selected.add(key);
      }
      customInput.value = '';
      sync();
    });
  }

  // initial paint
  sync();

  // --- Require at least one skill before continuing
  if (form) {
    form.addEventListener('submit', (e) => {
      if (selected.size === 0) {
        e.preventDefault();
        selectedBox.classList.add('invalid-block');
        // show small helper once
        let hint = selectedBox.nextElementSibling;
        if (!hint || !hint.classList || !hint.classList.contains('client-error')) {
          hint = document.createElement('div');
          hint.className = 'client-error';
          hint.textContent = 'Please add at least one skill.';
          selectedBox.parentNode.insertBefore(hint, selectedBox.nextSibling);
        }
        // focus the custom input for quick fix
        if (customInput) customInput.focus();
      }
    });
    // remove invalid style when a skill is added
    const clearBlock = () => {
      selectedBox.classList.remove('invalid-block');
      const hint = selectedBox.nextElementSibling;
      if (hint && hint.classList && hint.classList.contains('client-error')) hint.remove();
    };
    // hook into sync by observing size changes via renderSelected
    const origRender = renderSelected;
    renderSelected = function() { // monkey patch local function reference
      origRender();
      if (selected.size > 0) clearBlock();
    };
  }
});
