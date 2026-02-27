// --- live character counters ---
function bindCounter(id, outId) {
  const el = document.getElementById(id);
  const out = document.getElementById(outId);
  if (!el || !out) return;
  const max = Number(el.dataset.max || 2000);
  const update = () => { out.textContent = Math.min(el.value.length, max); };
  el.addEventListener('input', update);
  update();
}
bindCounter('description', 'descCount');
bindCounter('requirements', 'reqCount');

function togglePayFields(type) {
  const hr = document.getElementById('hourly_fields');
  const yr = document.getElementById('yearly_fields');
  if (!hr || !yr) return;
  if (type === 'hour') { hr.removeAttribute('hidden'); yr.setAttribute('hidden',''); }
  else { hr.setAttribute('hidden',''); yr.removeAttribute('hidden'); }
}
// initialize on load
const salaryType = document.getElementById('salary_type');
if (salaryType) togglePayFields(salaryType.value);

// --- simple chips input -> hidden CSV ---
(function(){
  const wrapper = document.getElementById('chips');
  if (!wrapper) return;
  const hidden = document.getElementById(wrapper.dataset.input);
  const input = wrapper.querySelector('.chip-input');
  const maxTags = 5;
  const tagsField = document.getElementById('tagsField');
  const tagsError = document.getElementById('tagsError');

  const tags = [];
  const normalize = (v) => v.replace(/\s+/g, ' ').trim();

  const seed = (hidden.value || '')
    .split(',')
    .map((v) => normalize(v))
    .filter(Boolean);
  seed.forEach((tag) => {
    if (!tags.some((t) => t.toLowerCase() === tag.toLowerCase())) tags.push(tag);
  });

  const render = () => {
    // remove old chips (except input)
    [...wrapper.querySelectorAll('.chip')].forEach(c => c.remove());
    tags.forEach((t, i) => {
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.textContent = t;
      const x = document.createElement('button');
      x.type = 'button';
      x.className = 'chip-x';
      x.setAttribute('aria-label', `Remove ${t}`);
      x.textContent = '×';
      x.addEventListener('click', () => { tags.splice(i,1); sync(); });
      chip.appendChild(x);
      wrapper.insertBefore(chip, input);
    });
    hidden.value = tags.join(', ');
    if (tags.length <= maxTags && tagsError) {
      tagsError.hidden = true;
      tagsError.textContent = '';
      if (tagsField) tagsField.classList.remove('has-error');
    }
  };
  const sync = () => { render(); };

  const showTagError = (message) => {
    if (!tagsError) return;
    tagsError.textContent = message;
    tagsError.hidden = false;
    if (tagsField) tagsField.classList.add('has-error');
  };

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && input.value.trim()) {
      e.preventDefault();
      const val = normalize(input.value);
      const exists = val && tags.some((t) => t.toLowerCase() === val.toLowerCase());
      if (val && !exists && tags.length >= maxTags) {
        showTagError(`You can add up to ${maxTags} tags.`);
        return;
      }
      if (val && !exists) tags.push(val);
      input.value = '';
      sync();
    } else if (e.key === 'Backspace' && !input.value && tags.length) {
      // quick delete last
      tags.pop();
      sync();
    }
  });

  sync();
})();

// --- clear inline error state as user edits ---
(function () {
  const fields = document.querySelectorAll('.jp-field.has-error');
  if (!fields.length) return;

  const clearError = (field) => {
    field.classList.remove('has-error');
    const err = field.querySelector('.jp-error');
    if (err) err.remove();
  };

  fields.forEach((field) => {
    const controls = field.querySelectorAll('input, textarea, select');
    controls.forEach((control) => {
      const handler = () => clearError(field);
      control.addEventListener('input', handler, { once: true });
      control.addEventListener('change', handler, { once: true });
    });
  });
})();
