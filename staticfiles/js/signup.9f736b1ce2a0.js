// signup.js — password show/hide + strength meter + AJAX submit with redirect (commented)

document.addEventListener('DOMContentLoaded', () => {
  // --- Grabs ---
  const form = document.getElementById('signup-form');          // <form id="signup-form">
  const pwd = document.getElementById('id_password');           // password input (Django default id)
  const strengthEl = document.getElementById('password-strength'); // strength text container
  const toggle = document.getElementById('pwd-toggle');         // "Show Password" clickable element
  const errorBox = document.getElementById('form-errors');      // container to display form errors (optional)
  const nextInput = document.querySelector('input[name="next"]'); // hidden next redirect, if present

  // =========================
  // Helper: CSRF token from cookie (Django)
  // =========================
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return decodeURIComponent(parts.pop().split(';').shift());
    return null;
  }
  const csrftoken = getCookie('csrftoken');

  // =========================
  // Show / Hide password
  // =========================
  if (!input || !toggle) return;

  function flipVisibility() {
    const showing = pwd.type == 'text';
    pwd.type = showing ? 'password' : 'text';
    toggle.textContent = showing ? 'Show Password' : 'Hide Password';
  }

  toggle.addEventListener('click', flipVisibility);

  // Accessibility: allow Enter/Space to toggle
  toggle.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      flipVisibility();
    }
  });

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
    if (!strengthEl || !pwd) return;
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

  if (pwd) {
    pwd.addEventListener('input', updateStrength);
    updateStrength();
  }

  // =========================
  // AJAX submit + follow redirect
  // =========================
  if (form) {
    form.addEventListener('submit', async (e) => {
      // If you want to allow normal POST (no fetch), remove this preventDefault.
      e.preventDefault();

      // Clear old errors (if you render them here)
      if (errorBox) {
        errorBox.innerHTML = '';
        errorBox.hidden = true;
      }

      // Build form data payload
      const data = new FormData(form);
      // Pass along ?next= if you’re using it
      if (nextInput && nextInput.value) data.append('next', nextInput.value);

      try {
        const resp = await fetch(form.action, {
          method: 'POST',
          body: data,
          headers: {
            'X-Requested-With': 'XMLHttpRequest', // lets the server know it's AJAX
            'X-CSRFToken': csrftoken || '',
          },
          redirect: 'follow', // fetch will follow, but it won't auto-navigate the browser
        });

        // If the server returns JSON with a redirect key, use it
        const contentType = resp.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          const payload = await resp.json();
          if (resp.ok && payload.redirect) {
            window.location.href = payload.redirect; // ✅ explicit navigation
            return;
          }
          // Handle JSON-form errors (optional shape)
          if (!resp.ok && payload.errors && errorBox) {
            errorBox.hidden = false;
            errorBox.innerHTML = Array.isArray(payload.errors)
              ? payload.errors.map(e => `<li>${e}</li>`).join('')
              : `<li>${payload.message || 'Please correct the errors below.'}</li>`;
            return;
          }
        }

        // If the server did a normal redirect (302), fetch marks resp.redirected=true.
        if (resp.redirected && resp.url) {
          window.location.href = resp.url; // ✅ follow server redirect
          return;
        }

        // If we got HTML back (form re-render with errors), inject it or show a generic error.
        const html = await resp.text();
        // Option 1 (quick): fall back to hard redirect to dashboard on 200 OK.
        if (resp.ok) {
          // If you always redirect on success server-side, we should rarely hit this branch.
          // As a safe fallback:
          window.location.href = '/dashboard/';
          return;
        }

        // Option 2 (better UX): replace the form container with returned HTML so field errors show.
        // const wrapper = document.getElementById('signup-form-wrapper');
        // if (wrapper) wrapper.innerHTML = html;

        // Minimal fallback error message:
        if (errorBox) {
          errorBox.hidden = false;
          errorBox.innerHTML = '<li>Signup failed. Please correct the errors and try again.</li>';
        }
      } catch (err) {
        if (errorBox) {
          errorBox.hidden = false;
          errorBox.innerHTML = '<li>Network error. Please try again.</li>';
        }
        // In dev: console.error(err);
      }
    });
  }
});
