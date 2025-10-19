// signup.js — password show/hide + strength meter (cleaned, commented)

document.addEventListener('DOMContentLoaded', () => {
  // --- Grabs ---
  const pwd = document.getElementById('id_password');           // password input
  const strengthEl = document.getElementById('password-strength'); // strength text container
  const toggle = document.getElementById('pwd-toggle');          // "Show Password" text on the right

  if (!pwd) return; // Not on this page

  // =========================
  // Show / Hide password
  // =========================
  function setToggleLabel() {
    const showing = pwd.type === 'text';
    const txt = showing ? 'Hide Password' : 'Show Password';
    if (toggle) {
      toggle.textContent = txt;
      toggle.setAttribute('aria-label', txt);
      toggle.setAttribute('aria-pressed', String(showing));
    }
  }

  function flipVisibility() {
    // Toggle the input type
    pwd.type = (pwd.type === 'text') ? 'password' : 'text';
    setToggleLabel();
    pwd.focus(); // keep focus in the field
  }

  if (toggle) {
    setToggleLabel();                          // initialize the label
    toggle.addEventListener('click', flipVisibility);
    // Accessibility: make the span behave like a button from the keyboard too
    toggle.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        flipVisibility();
      }
    });
  }

  // =========================
  // Strength meter (lightweight)
  // =========================
  function score(val) {
    if (!val) return 0;
    let s = 0;
    if (val.length >= 8) s++;
    if (/[A-Z]/.test(val)) s++;
    if (/[a-z]/.test(val)) s++;
    if (/\d/.test(val)) s++;
    if (/[^A-Za-z0-9]/.test(val)) s++;
    return s; // 0..5
  }

  function label(s) {
    if (s <= 1) return 'Very weak';
    if (s <= 3) return 'Medium strength';
    return 'Strong password';
  }

  function updateStrength() {
    if (!strengthEl) return;
    const val = pwd.value || '';
    if (!val) {
      strengthEl.textContent = '';
      strengthEl.style.color = '';
      return;
    }
    const sc = score(val);
    strengthEl.textContent = label(sc);
    // Simple inline color; swap to CSS classes later if you prefer
    strengthEl.style.color = sc <= 1 ? '#b91c1c' : (sc <= 3 ? '#b45309' : '#065f46');
  }

  pwd.addEventListener('input', updateStrength);
  updateStrength();
});
