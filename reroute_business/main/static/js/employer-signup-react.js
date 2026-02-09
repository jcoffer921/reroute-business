// employer-signup-react.js
// React micro-frontend for employer signup (animation + graceful fallback)

(function() {
  const rootEl = document.getElementById('employer-signup-react-root');
  if (!rootEl) return;
  const React = window.React;
  const ReactDOM = window.ReactDOM;
  const MotionLib = window.framerMotion || {};
  if (!React || !ReactDOM) return;

  const { useState, useEffect, useMemo } = React;
  const e = React.createElement;
  const motion = MotionLib.motion || {
    div: React.forwardRef((props, ref) => e('div', { ...props, ref }, props.children)),
    form: React.forwardRef((props, ref) => e('form', { ...props, ref }, props.children)),
    button: React.forwardRef((props, ref) => e('button', { ...props, ref }, props.children)),
  };
  const AnimatePresence = MotionLib.AnimatePresence || (({ children }) => children);

  const clean = (v) => (v === undefined || v === null || v === 'None') ? '' : v;

  function getCSRFToken() {
    const m = document.cookie.match(/(?:^|;\\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function isJsonResponse(res) {
    const ct = res.headers.get('Content-Type') || '';
    return ct.includes('application/json');
  }

  const props = {
    action: clean(rootEl.dataset.action) || '/employer/signup/',
    firstName: clean(rootEl.dataset.firstName),
    lastName: clean(rootEl.dataset.lastName),
    email: clean(rootEl.dataset.email),
    company: clean(rootEl.dataset.company),
    website: clean(rootEl.dataset.website),
    description: clean(rootEl.dataset.description),
    initialErrors: (clean(rootEl.dataset.errors) || '').trim(),
    siteKey: clean(rootEl.dataset.sitekey),
    loginUrl: clean(rootEl.dataset.loginUrl) || '/employer/login/',
    userSignupUrl: clean(rootEl.dataset.userSignupUrl) || '/signup/',
    termsUrl: clean(rootEl.dataset.termsUrl) || '/terms/',
    privacyUrl: clean(rootEl.dataset.privacyUrl) || '/privacy/',
    googleUrl: clean(rootEl.dataset.googleUrl) || '',
    googleDivider: clean(rootEl.dataset.googleDivider),
  };

  function EmployerSignupApp(p) {
    const [firstName, setFirstName] = useState(p.firstName || '');
    const [lastName, setLastName] = useState(p.lastName || '');
    const [email, setEmail] = useState(p.email || '');
    const [password1, setPassword1] = useState('');
    const [password2, setPassword2] = useState('');
    const [company, setCompany] = useState(p.company || '');
    const [website, setWebsite] = useState(p.website || '');
    const [description, setDescription] = useState(p.description || '');
    const [agree, setAgree] = useState(false);
    const [showPwd1, setShowPwd1] = useState(false);
    const [showPwd2, setShowPwd2] = useState(false);
    const [error, setError] = useState(p.initialErrors);
    const [loading, setLoading] = useState(false);
    const [shakeKey, setShakeKey] = useState(0);
    const [captchaId, setCaptchaId] = useState(null);

    const legacyForm = useMemo(() => document.getElementById('employer-signup-form'), []);
    const hasRecaptcha = !!p.siteKey;

    useEffect(() => {
      document.body.classList.add('employer-signup-react-active');
      return () => document.body.classList.remove('employer-signup-react-active');
    }, []);

    useEffect(() => {
      if (!hasRecaptcha) return;
      let mounted = true;
      const tryRender = () => {
        if (!mounted) return;
        const g = window.grecaptcha;
        if (g && g.render && !captchaId) {
          const id = g.render('employer-signup-recaptcha', { sitekey: p.siteKey });
          setCaptchaId(id);
          return true;
        }
        return false;
      };
      if (!tryRender()) {
        const timer = setInterval(() => {
          if (tryRender()) clearInterval(timer);
        }, 300);
        return () => { mounted = false; clearInterval(timer); };
      }
      return () => { mounted = false; };
    }, [hasRecaptcha, p.siteKey, captchaId]);

    const variants = useMemo(() => ({
      item: {
        hidden: { opacity: 0, y: 12 },
        show: (i = 1) => ({
          opacity: 1,
          y: 0,
          transition: { duration: 0.35, delay: 0.05 * i, ease: 'easeOut' },
        }),
      },
      card: {
        hidden: { opacity: 0, y: 16 },
        show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: 'easeOut' } },
        shake: {
          x: [0, -8, 8, -6, 6, -2, 0],
          transition: { duration: 0.45, ease: 'easeInOut' },
        },
      },
      error: {
        hidden: { opacity: 0, y: -6 },
        show: { opacity: 1, y: 0, transition: { duration: 0.28 } },
        exit: { opacity: 0, y: -6, transition: { duration: 0.2 } },
      },
    }), []);

    function syncLegacyForm() {
      if (!legacyForm) return;
      const map = {
        first_name: firstName,
        last_name: lastName,
        email,
        password1,
        password2,
        company_name: company,
        website,
        description,
        agree_terms: agree ? '1' : '',
      };
      Object.entries(map).forEach(([name, val]) => {
        const input = legacyForm.querySelector(`[name="${name}"]`);
        if (!input) return;
        if (input.type === 'checkbox') input.checked = !!val;
        else input.value = val;
      });
    }

    async function handleSubmit(event) {
      event.preventDefault();

      if (!firstName || !lastName || !email || !password1 || !password2 || !company) {
        setError('Please fill in all required fields.');
        setShakeKey((k) => k + 1);
        return;
      }
      if (password1 !== password2) {
        setError('Passwords must match.');
        setShakeKey((k) => k + 1);
        return;
      }
      if (!agree) {
        setError('Please agree to the Terms and Privacy Policy.');
        setShakeKey((k) => k + 1);
        return;
      }

      // reCAPTCHA → fall back to legacy form
      if (hasRecaptcha) {
        syncLegacyForm();
        legacyForm?.submit();
        return;
      }

      setLoading(true);
      setError('');

      try {
        const payload = hasRecaptcha ? new FormData() : null;
        if (payload) {
          payload.append('first_name', firstName);
          payload.append('last_name', lastName);
          payload.append('email', email);
          payload.append('password1', password1);
          payload.append('password2', password2);
          payload.append('company_name', company);
          payload.append('website', website);
          payload.append('description', description);
          payload.append('agree_terms', agree ? '1' : '');
          const token = (window.grecaptcha && captchaId !== null)
            ? window.grecaptcha.getResponse(captchaId)
            : '';
          if (!token) {
            setError('Please complete the captcha challenge.');
            setShakeKey((k) => k + 1);
            setLoading(false);
            return;
          }
          payload.append('g-recaptcha-response', token);
        }

        const res = await fetch(p.action, {
          method: 'POST',
          headers: hasRecaptcha ? {
            'Accept': 'application/json',
            'X-CSRFToken': getCSRFToken(),
            'X-Requested-With': 'XMLHttpRequest',
          } : {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CSRFToken': getCSRFToken(),
            'X-Requested-With': 'XMLHttpRequest',
          },
          credentials: 'same-origin',
          body: hasRecaptcha ? payload : JSON.stringify({
            first_name: firstName,
            last_name: lastName,
            email,
            password1,
            password2,
            company_name: company,
            website,
            description,
            agree_terms: agree,
          }),
        });

        if (!isJsonResponse(res)) {
          syncLegacyForm();
          if (hasRecaptcha && legacyForm && window.grecaptcha && captchaId !== null) {
            const token = window.grecaptcha.getResponse(captchaId);
            let hidden = legacyForm.querySelector('input[name="g-recaptcha-response"]');
            if (!hidden) {
              hidden = document.createElement('input');
              hidden.type = 'hidden';
              hidden.name = 'g-recaptcha-response';
              legacyForm.appendChild(hidden);
            }
            hidden.value = token;
          }
          legacyForm?.submit();
          return;
        }

        const data = await res.json().catch(() => ({}));

        if (res.ok) {
          window.location.assign(data.redirect || '/employer/dashboard/');
          return;
        }

        setError(data.message || 'Signup failed. Please correct the errors.');
        setShakeKey((k) => k + 1);
      } catch (err) {
        setError('Something went wrong. Please try again.');
        setShakeKey((k) => k + 1);
      } finally {
        setLoading(false);
      }
    }

    return e(
      motion.div,
      {
        className: 'react-login-shell',
        variants: variants.card,
        initial: 'hidden',
        animate: error ? 'shake' : 'show',
        key: shakeKey,
      },
      [
        e(
          'div',
          { className: 'react-header', key: 'header' },
          [
            e('div', { className: 'spark', 'aria-hidden': 'true' }, '✺'),
            e('div', { className: 'header-copy' }, [
              e('h1', { className: 'auth-title' }, 'Create your employer account'),
              e('p', { className: 'react-subtitle' }, 'Post jobs, review applicants, and manage your company profile.'),
            ]),
          ]
        ),
        e('span', { className: 'auth-pill pill-inline', key: 'pill' }, 'Welcome aboard'),
        e(
          motion.form,
          {
            key: 'form',
            className: 'react-stack',
            onSubmit: handleSubmit,
            noValidate: true,
          },
          [
            e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 1, className: 'react-field' },
              [
                e('div', { className: 'label-row' }, [
                  e('label', { htmlFor: 'employer-first-name' }, 'First name'),
                ]),
                e('input', {
                  id: 'employer-first-name',
                  name: 'first_name',
                  type: 'text',
                  autoComplete: 'given-name',
                  placeholder: 'Alex',
                  value: firstName,
                  onChange: (evt) => setFirstName(evt.target.value),
                  required: true,
                }),
              ]
            ),
            e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 2, className: 'react-field' },
              [
                e('div', { className: 'label-row' }, [
                  e('label', { htmlFor: 'employer-last-name' }, 'Last name'),
                ]),
                e('input', {
                  id: 'employer-last-name',
                  name: 'last_name',
                  type: 'text',
                  autoComplete: 'family-name',
                  placeholder: 'Rivera',
                  value: lastName,
                  onChange: (evt) => setLastName(evt.target.value),
                  required: true,
                }),
              ]
            ),
            e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 3, className: 'react-field' },
              [
                e('div', { className: 'label-row' }, [
                  e('label', { htmlFor: 'employer-email' }, 'Work email'),
                ]),
                e('input', {
                  id: 'employer-email',
                  name: 'email',
                  type: 'email',
                  inputMode: 'email',
                  autoComplete: 'email',
                  placeholder: 'name@company.com',
                  value: email,
                  onChange: (evt) => setEmail(evt.target.value),
                  required: true,
                }),
              ]
            ),
            e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 4, className: 'react-field' },
              [
                e('div', { className: 'label-row' }, [
                  e('label', { htmlFor: 'employer-password1' }, 'Password'),
                  e('span', { className: 'micro-hint' }, 'Use at least 8 characters.'),
                ]),
                e('div', { className: 'react-meta' }, [
                  e('input', {
                    id: 'employer-password1',
                    name: 'password1',
                    type: showPwd1 ? 'text' : 'password',
                    autoComplete: 'new-password',
                    placeholder: '••••••••',
                    value: password1,
                    onChange: (evt) => setPassword1(evt.target.value),
                    required: true,
                    style: { flex: 1 },
                  }),
                  e('button', {
                    type: 'button',
                    className: 'pwd-toggle-chip',
                    onClick: () => setShowPwd1((s) => !s),
                    'aria-pressed': showPwd1,
                    'aria-controls': 'employer-password1',
                  }, showPwd1 ? 'Hide' : 'Show'),
                ]),
              ]
            ),
            e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 5, className: 'react-field' },
              [
                e('div', { className: 'label-row' }, [
                  e('label', { htmlFor: 'employer-password2' }, 'Confirm password'),
                ]),
                e('div', { className: 'react-meta' }, [
                  e('input', {
                    id: 'employer-password2',
                    name: 'password2',
                    type: showPwd2 ? 'text' : 'password',
                    autoComplete: 'new-password',
                    placeholder: '••••••••',
                    value: password2,
                    onChange: (evt) => setPassword2(evt.target.value),
                    required: true,
                    style: { flex: 1 },
                  }),
                  e('button', {
                    type: 'button',
                    className: 'pwd-toggle-chip',
                    onClick: () => setShowPwd2((s) => !s),
                    'aria-pressed': showPwd2,
                    'aria-controls': 'employer-password2',
                  }, showPwd2 ? 'Hide' : 'Show'),
                ]),
              ]
            ),
            e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 6, className: 'react-field' },
              [
                e('div', { className: 'label-row' }, [
                  e('label', { htmlFor: 'employer-company' }, 'Company name'),
                ]),
                e('input', {
                  id: 'employer-company',
                  name: 'company_name',
                  type: 'text',
                  placeholder: 'Company Inc.',
                  value: company,
                  onChange: (evt) => setCompany(evt.target.value),
                  required: true,
                }),
              ]
            ),
            e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 7, className: 'react-field' },
              [
                e('div', { className: 'label-row' }, [
                  e('label', { htmlFor: 'employer-website' }, 'Website (optional)'),
                ]),
                e('input', {
                  id: 'employer-website',
                  name: 'website',
                  type: 'url',
                  placeholder: 'https://example.com',
                  value: website,
                  onChange: (evt) => setWebsite(evt.target.value),
                }),
              ]
            ),
            e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 8, className: 'react-field' },
              [
                e('div', { className: 'label-row' }, [
                  e('label', { htmlFor: 'employer-description' }, 'Company description (optional)'),
                ]),
                e('textarea', {
                  id: 'employer-description',
                  name: 'description',
                  rows: 4,
                  placeholder: 'Tell candidates about your mission, team size, and benefits.',
                  value: description,
                  onChange: (evt) => setDescription(evt.target.value),
                }),
              ]
            ),
            hasRecaptcha ? e(
              motion.div,
              {
                variants: variants.item,
                initial: 'hidden',
                animate: 'show',
                custom: 9,
                className: 'g-recaptcha',
                id: 'employer-signup-recaptcha',
                'data-sitekey': p.siteKey,
              },
              null
            ) : null,
            e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 10, className: 'react-meta' },
              [
                e('label', { className: 'checkbox' }, [
                  e('input', {
                    type: 'checkbox',
                    name: 'agree_terms',
                    checked: agree,
                    onChange: (evt) => setAgree(evt.target.checked),
                  }),
                  e('span', null, [
                    'I agree to the ',
                    e('a', { href: p.termsUrl, target: '_blank', rel: 'noopener' }, 'Terms'),
                    ' and ',
                    e('a', { href: p.privacyUrl, target: '_blank', rel: 'noopener' }, 'Privacy Policy'),
                    '.',
                  ]),
                ]),
              ]
            ),
            e(
              motion.button,
              {
                type: 'submit',
                className: 'btn-pill',
                disabled: loading,
                variants: variants.item,
                initial: 'hidden',
                animate: 'show',
                custom: 11,
              },
              e('span', { className: 'btn-content' }, [
                loading ? e('span', { className: 'btn-spinner', 'aria-hidden': 'true' }) : null,
                loading ? 'Creating account…' : 'Create employer account',
              ])
            ),
            p.googleUrl ? e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 12, className: 'oauth-block' },
              [
                e('div', { className: 'oauth-divider' }, [
                  e('span', { className: 'oauth-divider-line', 'aria-hidden': 'true' }),
                  e('span', { className: 'oauth-divider-text' }, p.googleDivider || 'Or sign up with'),
                  e('span', { className: 'oauth-divider-line', 'aria-hidden': 'true' }),
                ]),
                e('a', { className: 'oauth-google-btn', href: p.googleUrl }, [
                  e('span', { className: 'oauth-google-icon', 'aria-hidden': 'true' }, e(
                    'svg',
                    { width: 18, height: 18, viewBox: '0 0 48 48', role: 'img', 'aria-hidden': 'true', focusable: 'false' },
                    [
                      e('path', { fill: '#EA4335', d: 'M24 9.5c3.54 0 6.7 1.23 9.19 3.25l6.86-6.86C35.96 2.36 30.3 0 24 0 14.64 0 6.53 5.39 2.56 13.22l7.98 6.19C12.41 13.06 17.74 9.5 24 9.5z' }),
                      e('path', { fill: '#4285F4', d: 'M46.5 24.5c0-1.6-.14-3.15-.41-4.65H24v9h12.71c-.55 2.95-2.23 5.45-4.73 7.13l7.29 5.67C43.9 37.34 46.5 31.4 46.5 24.5z' }),
                      e('path', { fill: '#FBBC05', d: 'M10.54 28.41a14.5 14.5 0 0 1 0-8.82l-7.98-6.19A23.99 23.99 0 0 0 0 24c0 3.95.95 7.68 2.56 11.02l7.98-6.61z' }),
                      e('path', { fill: '#34A853', d: 'M24 48c6.48 0 11.93-2.14 15.9-5.85l-7.29-5.67c-2.03 1.36-4.64 2.17-8.61 2.17-6.26 0-11.59-3.56-13.46-8.91l-7.98 6.61C6.53 42.61 14.64 48 24 48z' }),
                    ]
                  )),
                  e('span', null, 'Continue with Google'),
                ]),
              ]
            ) : null,
            e(
              AnimatePresence,
              { key: 'error-presence' },
              error ? e(
                motion.div,
                {
                  className: 'react-error-banner',
                  role: 'alert',
                  'aria-live': 'polite',
                  variants: variants.error,
                  initial: 'hidden',
                  animate: 'show',
                  exit: 'exit',
                },
                error
              ) : null
            ),
          ]
        ),
        e(
          motion.div,
          { variants: variants.item, initial: 'hidden', animate: 'show', custom: 13, className: 'secondary-actions' },
          [
            e('span', null, [
              'Already have an account? ',
              e('a', { className: 'link', href: p.loginUrl }, 'Employer login'),
              '.',
            ]),
            e('span', { className: 'sep', 'aria-hidden': 'true' }, '·'),
            e('a', { className: 'link', href: p.userSignupUrl }, 'User signup'),
          ]
        ),
      ]
    );
  }

  ReactDOM.createRoot(rootEl).render(e(EmployerSignupApp, props));
})();
