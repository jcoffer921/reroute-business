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
  if (type === 'hour') { hr.style.display = ''; yr.style.display = 'none'; }
  else { hr.style.display = 'none'; yr.style.display = ''; }
}
// initialize on load
togglePayFields(document.getElementById('salary_type').value);

// --- simple chips input -> hidden CSV ---
(function(){
  const wrapper = document.getElementById('chips');
  if (!wrapper) return;
  const hidden = document.getElementById(wrapper.dataset.input);
  const input = wrapper.querySelector('.chip-input');

  const tags = [];
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
      x.onclick = () => { tags.splice(i,1); sync(); };
      chip.appendChild(x);
      wrapper.insertBefore(chip, input);
    });
    hidden.value = tags.join(', ');
  };
  const sync = () => { render(); };

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && input.value.trim()) {
      e.preventDefault();
      const val = input.value.trim();
      if (!tags.includes(val)) tags.push(val);
      input.value = '';
      sync();
    } else if (e.key === 'Backspace' && !input.value && tags.length) {
      // quick delete last
      tags.pop();
      sync();
    }
  });
})();