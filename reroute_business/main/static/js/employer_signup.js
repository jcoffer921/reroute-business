/* ===========================================================
   Employer Signup — UX helpers (no fetch; progressive enhance)
   - Live validation (required fields, email, passwords)
   - Inline errors next to fields
   - Password strength + match hint
   - Website normalization (adds https:// if missing)
   - Disables submit to avoid double posts
   -----------------------------------------------------------
   This script assumes IDs from your template:
     first_name, last_name, email, password1, password2,
     company_name, website, description
   =========================================================== */

(function () {
  'use strict';

  // ----- Quick DOM helpers -----
  const qs  = (sel, el = document) => el.querySelector(sel);
  const qsa = (sel, el = document) => Array.from(el.querySelectorAll(sel));
  const on  = (el, ev, fn) => el && el.addEventListener(ev, fn);

  const form        = qs('form[action$="/employer/signup/"]') || qs('form[action*="employer_signup"]') || qs('form');
  if (!form) return; // not on this page

  const firstName   = qs('#first_name');
  const lastName    = qs('#last_name');
  const email       = qs('#email');
  const pw1         = qs('#password1');
  const pw2         = qs('#password2');
  const company     = qs('#company_name');
  const website     = qs('#website');
  const agree       = qs('input[name="agree_terms"]');
  const submitBtn   = form.querySelector('button[type="submit"]');

  // Show/Hide toggles for password1/password2 if present
  const toggles = qsa('.pwd-toggle-text', form);
  toggles.forEach(t => {
    const targetId = t.getAttribute('aria-controls') || t.getAttribute('data-target');
    const input = targetId ? qs('#' + CSS.escape(targetId), form) : null;
    if (!input) return;
    function flip() {
      const showing = input.type === 'text';
      input.type = showing ? 'password' : 'text';
      t.textContent = showing ? 'Show Password' : 'Hide Password';
      input.focus();
    }
    t.addEventListener('click', flip);
    t.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); flip(); }
    });
  });

  // We’ll show strength/match hints just under the password inputs
  const pwStrength  = document.createElement('div');
  pwStrength.className = 'field-hint';
  pwStrength.setAttribute('aria-live', 'polite');
  pw1?.parentElement?.appendChild(pwStrength);

  const pwMatch     = document.createElement('div');
  pwMatch.className = 'field-hint';
  pwMatch.setAttribute('aria-live', 'polite');
  pw2?.parentElement?.appendChild(pwMatch);

  // ----- Error helpers -----
  function getErrorEl(input) {
    // Find an existing .field-error sibling, or create one
    let el = input?.parentElement?.querySelector('.field-error');
    if (!el && input?.parentElement) {
      el = document.createElement('div');
      el.className = 'field-error';
      input.parentElement.appendChild(el);
    }
    return el;
  }

  function setError(input, msg) {
    const el = getErrorEl(input);
    if (el) el.textContent = msg || '';
    input?.classList.add('has-error');
  }

  function clearError(input) {
    const el = getErrorEl(input);
    if (el) el.textContent = '';
    input?.classList.remove('has-error');
  }

  // ----- Validators -----
  const isEmail = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v || '');

  function scorePassword(v) {
    // Lightweight password score: 0..4
    if (!v) return 0;
    let s = 0;
    if (v.length >= 8) s++;
    if (/[A-Z]/.test(v)) s++;
    if (/[a-z]/.test(v)) s++;
    if (/\d|[^A-Za-z0-9]/.test(v)) s++;
    return s;
  }

  function strengthLabel(score) {
    return ['Very weak', 'Weak', 'Okay', 'Good', 'Strong'][score] || 'Weak';
  }

  // Live field validation
  function validateFirst() {
    const v = (firstName?.value || '').trim();
    if (!v) { setError(firstName, 'First name is required.'); return false; }
    clearError(firstName); return true;
  }
  function validateLast() {
    const v = (lastName?.value || '').trim();
    if (!v) { setError(lastName, 'Last name is required.'); return false; }
    clearError(lastName); return true;
  }
  function validateEmail() {
    const v = (email?.value || '').trim();
    if (!v) { setError(email, 'Email is required.'); return false; }
    if (!isEmail(v)) { setError(email, 'Enter a valid email.'); return false; }
    clearError(email); return true;
  }
  function validateCompany() {
    const v = (company?.value || '').trim();
    if (!v) { setError(company, 'Company name is required.'); return false; }
    clearError(company); return true;
  }
  function validatePw1() {
    const v = pw1?.value || '';
    const score = scorePassword(v);
    pwStrength.textContent = v ? `Strength: ${strengthLabel(score)}` : '';
    if (!v) { setError(pw1, 'Password is required.'); return false; }
    if (v.length < 8) { setError(pw1, 'Use at least 8 characters.'); return false; }
    clearError(pw1); return true;
  }
  function validatePw2() {
    const v1 = pw1?.value || '';
    const v2 = pw2?.value || '';
    if (!v2) { setError(pw2, 'Confirm your password.'); pwMatch.textContent=''; return false; }
    const ok = v1 === v2;
    pwMatch.textContent = ok ? 'Passwords match.' : 'Passwords do not match.';
    if (!ok) { setError(pw2, 'Passwords do not match.'); return false; }
    clearError(pw2); return true;
  }
  function validateAgree() {
    if (agree && !agree.checked) { setError(agree, 'You must agree to continue.'); return false; }
    clearError(agree); return true;
  }

  // ----- Website normalization -----
  function normalizeWebsite() {
    const v = (website?.value || '').trim();
    if (!v) return true; // optional
    // Add protocol if missing
    if (!/^https?:\/\//i.test(v)) {
      website.value = 'https://' + v;
    }
    // Very light format check
    try { new URL(website.value); clearError(website); return true; }
    catch { setError(website, 'Enter a valid URL or leave blank.'); return false; }
  }

  // ----- Wire live validation -----
  on(firstName, 'blur', validateFirst);
  on(lastName, 'blur', validateLast);
  on(email, 'blur', validateEmail);
  on(company, 'blur', validateCompany);
  on(pw1, 'input', () => { validatePw1(); validatePw2(); });
  on(pw2, 'input', validatePw2);
  on(website, 'blur', normalizeWebsite);
  on(agree, 'change', validateAgree);

  // ----- Submit handling -----
  on(form, 'submit', (e) => {
    // Run all validations; if any fail, stop submission and focus the first error
    const checks = [
      validateFirst(),
      validateLast(),
      validateEmail(),
      validateCompany(),
      validatePw1(),
      validatePw2(),
      normalizeWebsite(),
      validateAgree()
    ];
    if (checks.includes(false)) {
      e.preventDefault();
      // Focus first field with error for accessibility
      const firstError = qs('.has-error', form) || qs('.field-error:not(:empty)', form);
      if (firstError?.focus) firstError.focus();
      return;
    }

    // Prevent double submit
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Creating account…';
    }
  });
})();
