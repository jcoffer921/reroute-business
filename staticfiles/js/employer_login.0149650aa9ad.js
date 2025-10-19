// employer_login.js
// Handles ONLY the Employer Login form via JSON → /employer/login/

// -------------------- Helpers --------------------

/** Get Django CSRF token (prefer hidden input, fallback to cookie) */
function getCSRFToken(form) {
  // Look for the hidden input Django adds in the form
  const input = form.querySelector('input[name="csrfmiddlewaretoken"]');
  if (input && input.value) return input.value;

  // Fallback: read csrftoken cookie
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}

/** Decide redirect: server redirect → hidden next → default employer dashboard */
function resolveRedirect(serverRedirect, nextValue) {
  return serverRedirect || nextValue || '/employer/dashboard/';
}

/** Quick check: is this response JSON? */
function isJsonResponse(res) {
  const ct = res.headers.get('Content-Type') || '';
  return ct.includes('application/json');
}

// -------------------- Main Handler --------------------

/** Submit employer login as JSON to the form's action (should be /employer/login/) */
async function handleEmployerLoginSubmit(event) {
  event.preventDefault(); // stop normal form submit

  const form = event.currentTarget;
  const action = form.getAttribute('action') || '/employer/login/'; // keep it employer-only
  const errorEl = document.getElementById('login-error'); // optional inline error element

  // Grab fields by employer IDs first, then fall back to name attributes
  const usernameEl =
    form.querySelector('#employer-username') || form.querySelector('input[name="username"]');
  const passwordEl =
    form.querySelector('#employer-password') || form.querySelector('input[name="password"]');
  const nextEl = form.querySelector('input[name="next"]');

  const username = (usernameEl?.value || '').trim();
  const password = passwordEl?.value || '';
  const nextValue = nextEl?.value || '';

  // Basic validation
  if (!username || !password) {
    if (errorEl) errorEl.textContent = 'Please enter your username and password.';
    else alert('Please enter your username and password.');
    return;
  }

  // Button UX
  const submitBtn =
    form.querySelector('#employer-login-btn') || form.querySelector('button[type="submit"]');
  const originalBtnText = submitBtn ? submitBtn.textContent : '';
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Signing in...';
  }
  if (errorEl) errorEl.textContent = '';

  try {
    const res = await fetch(action, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',          // hits JSON branch in employer_login_view
        'Accept': 'application/json',                // be explicit about what we expect back
        'X-CSRFToken': getCSRFToken(form),           // CSRF for Django
        'X-Requested-With': 'XMLHttpRequest',        // helps servers identify AJAX
      },
      credentials: 'same-origin',
      body: JSON.stringify({ username, password, next: nextValue }),
    });

    // If we got HTML (not JSON), fall back to normal submit so server handles it.
    if (!isJsonResponse(res)) {
      form.removeEventListener('submit', handleEmployerLoginSubmit);
      form.submit();
      return;
    }

    const data = await res.json().catch(() => ({}));

    if (res.ok && (data.status === 'success' || data.redirect)) {
      // Success path: server told us where to go (or we use next/default)
      window.location.assign(resolveRedirect(data.redirect, nextValue));
      return;
    }

    // Known error statuses with JSON body
    if ([400, 401, 403].includes(res.status)) {
      const msg =
        data.message ||
        (res.status === 403 ? 'You do not have employer access.' : 'Invalid credentials.');
      if (errorEl) errorEl.textContent = msg;
      else alert(msg);
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = originalBtnText;
      }
      return;
    }

    // Unexpected but JSON: show generic message
    if (errorEl) errorEl.textContent = 'Login failed. Please try again.';
    else alert('Login failed. Please try again.');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = originalBtnText;
    }
  } catch (e) {
    // Network/JS failure → show message and re-enable
    if (errorEl) errorEl.textContent = 'Something went wrong. Please try again.';
    else alert('Something went wrong. Please try again.');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = originalBtnText;
    }
  }
}

// -------------------- Wire Up --------------------

document.addEventListener('DOMContentLoaded', () => {
  // Only attach on the employer login page
  const form = document.getElementById('login-form'); // employer template should use this id
  if (form && (form.getAttribute('action') || '').includes('/employer/login')) {
    form.addEventListener('submit', handleEmployerLoginSubmit);
  }
});
