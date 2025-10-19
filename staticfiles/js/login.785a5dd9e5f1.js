// login.js
// ===================================================================
// Unified login (user + employer)
// - Posts JSON to the form's action
// - Finds fields robustly across templates
// - Disables button while submitting
// - Inline Show/Hide Password + Caps Lock hint
// - Safe redirect handling and graceful fallback
// ===================================================================

// ---- CSRF helper (Django default cookie) ----
function getCSRFToken() {
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}

// ---- Prefer server redirect; otherwise use next; otherwise sane default ----
function doRedirect(redirectUrl, nextValue, isEmployer) {
  const fallback = isEmployer ? '/employer/dashboard/' : '/dashboard/';
  window.location.assign(redirectUrl || nextValue || fallback);
}

// ---- Is the response JSON? ----
function isJsonResponse(res) {
  const ct = res.headers.get('Content-Type') || '';
  return ct.includes('application/json');
}

// ---- Main submit handler ----
async function submitLogin(event) {
  event.preventDefault();

  const form = event.currentTarget;
  const action = form.getAttribute('action') || '/login/';
  const isEmployer = action.includes('/employer/');

  // Be tolerant of different IDs/names between templates
  const userEl =
    document.getElementById('login-username') ||
    document.getElementById('id_username') ||
    form.querySelector('input[name="username"]') ||
    form.querySelector('input[name="email"]');

  const pwdEl =
    document.getElementById('login-password') ||
    document.getElementById('employer-password') ||
    document.getElementById('id_password') ||
    form.querySelector('input[type="password"][name="password"]');

  const nextEl = form.querySelector('input[name="next"]');
  const errorEl = document.getElementById('login-error') || document.getElementById('form-error');

  const username = (userEl?.value || '').trim();
  const password = pwdEl?.value || '';
  const nextValue = nextEl?.value || '';

  // Simple client guard so we don't POST empty
  if (!username || !password) {
    if (errorEl) errorEl.textContent = 'Please enter your username/email and password.';
    userEl?.focus();
    return;
  }

  // Button UX
  const submitBtn = form.querySelector('#signin-btn, button[type="submit"]');
  const originalBtnText = submitBtn ? submitBtn.textContent : '';
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Signing in…';
  }
  if (errorEl) errorEl.textContent = '';

  try {
    const res = await fetch(action, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-CSRFToken': getCSRFToken(),
        'X-Requested-With': 'XMLHttpRequest',
      },
      credentials: 'same-origin',
      body: JSON.stringify({ username, email: username, password, next: nextValue }),
    });

    // If not JSON (e.g., server returned HTML), fall back to normal form submit
    if (!isJsonResponse(res)) {
      form.removeEventListener('submit', submitLogin);
      form.submit();
      return;
    }

    const data = await res.json().catch(() => ({}));

    if (res.ok) {
      doRedirect(data.redirect, nextValue, isEmployer);
      return;
    }

    // Known errors: show the message and re-enable
    if ([400, 401, 403].includes(res.status)) {
      if (errorEl) errorEl.textContent = data.message || 'Login failed. Please try again.';
      if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = originalBtnText; }
      return;
    }

    // Unexpected JSON error—fallback to normal submit
    form.removeEventListener('submit', submitLogin);
    form.submit();
  } catch (err) {
    if (errorEl) errorEl.textContent = 'Something went wrong. Please try again.';
    if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = originalBtnText; }
  }
}

// ---- Tiny UX helpers (moved from inline to here) ----
function wireUXHelpers() {
  const form = document.getElementById('login-form');
  const btn = document.getElementById('signin-btn');
  const pwd =
    document.getElementById('login-password') ||
    document.getElementById('employer-password') ||
    document.getElementById('id_password');

  // Support either a button or text span for the toggle
  const toggle =
    document.querySelector('.pwd-toggle, .pwd-toggle-text'); // matches either class
  const caps = document.getElementById('caps-hint');
  const errorBox = document.getElementById('form-error');

  // Disable while submitting (HTML form path)
  form?.addEventListener('submit', () => {
    if (btn) { btn.disabled = true; btn.textContent = 'Signing in…'; }
  });

  // Show/Hide password
  function setToggleLabel() {
    if (!toggle || !pwd) return;
    const showing = pwd.type === 'text';
    const txt = showing ? 'Hide Password' : 'Show Password';
    toggle.textContent = txt;
    toggle.setAttribute('aria-label', txt);
    toggle.setAttribute('aria-pressed', String(showing));
  }
  function flip() {
    if (!pwd || !toggle) return;
    pwd.type = (pwd.type === 'text') ? 'password' : 'text';
    setToggleLabel();
    pwd.focus();
  }
  if (toggle && pwd) {
    setToggleLabel();
    toggle.addEventListener('click', flip);
    toggle.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); flip(); }
    });
  }

  // Caps Lock hint
  function setCaps(e) {
    if (!caps) return;
    const on = e.getModifierState && e.getModifierState('CapsLock');
    caps.hidden = !on;
  }
  pwd?.addEventListener('keydown', setCaps);
  pwd?.addEventListener('keyup', setCaps);

  // Focus any server-rendered error for screen readers
  if (errorBox && errorBox.textContent.trim().length) errorBox.focus();
}

// ---- Wire up on DOM ready ----
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('login-form');
  if (form) {
    // Attach AJAX submit
    form.addEventListener('submit', submitLogin);
  }
  // Attach UX helpers (works for both user & employer pages)
  wireUXHelpers();
});
