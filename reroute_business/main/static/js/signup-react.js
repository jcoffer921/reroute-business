// signup-react.js
// React micro-frontend for the user signup page (motion-based, no build step)

(function() {
  const rootEl = document.getElementById('signup-react-root');
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

  function scorePassword(val) {
    if (!val) return 0;
    let s = 0;
    if (val.length >= 8) s++;
    if (/[A-Z]/.test(val)) s++;
    if (/[a-z]/.test(val)) s++;
    if (/\d/.test(val)) s++;
    if (/[^A-Za-z0-9]/.test(val)) s++;
    return s;
  }

  const props = {
    action: clean(rootEl.dataset.action) || '/signup/',
    nextValue: clean(rootEl.dataset.next) || '/dashboard/',
    firstName: clean(rootEl.dataset.firstName),
    lastName: clean(rootEl.dataset.lastName),
    username: clean(rootEl.dataset.username),
    email: clean(rootEl.dataset.email),
    initialErrors: (clean(rootEl.dataset.errors) || '').trim(),
    siteKey: clean(rootEl.dataset.sitekey),
    loginUrl: clean(rootEl.dataset.loginUrl) || '/login/',
    termsUrl: clean(rootEl.dataset.termsUrl) || '/terms/',
    privacyUrl: clean(rootEl.dataset.privacyUrl) || '/privacy/',
    googleUrl: clean(rootEl.dataset.googleUrl) || '',
    googleDivider: clean(rootEl.dataset.googleDivider),
  };

  function SignupApp(p) {
    const [firstName, setFirstName] = useState(p.firstName || '');
    const [lastName, setLastName] = useState(p.lastName || '');
    const [username, setUsername] = useState(p.username || '');
    const [email, setEmail] = useState(p.email || '');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);
    const [error, setError] = useState(p.initialErrors);
    const [loading, setLoading] = useState(false);
    const [shakeKey, setShakeKey] = useState(0);
    const [capsOn, setCapsOn] = useState(false);
    const [captchaId, setCaptchaId] = useState(null);

    const legacyForm = useMemo(() => document.getElementById('signup-form'), []);
    const hasRecaptcha = !!p.siteKey;

    useEffect(() => {
      document.body.classList.add('signup-react-active');
      return () => document.body.classList.remove('signup-react-active');
    }, []);

    useEffect(() => {
      if (!hasRecaptcha) return;
      let mounted = true;
      const tryRender = () => {
        if (!mounted) return;
        const g = window.grecaptcha;
        if (g && g.render && !captchaId) {
          const id = g.render('signup-recaptcha', { sitekey: p.siteKey });
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

    const strength = scorePassword(password);
    const strengthLabel = password
      ? (strength <= 1 ? 'Very weak' : (strength <= 3 ? 'Medium strength' : 'Strong password'))
      : '';
    const strengthColor = strength <= 1 ? '#b91c1c' : (strength <= 3 ? '#b45309' : '#065f46');

    const onCapsCheck = (event) => {
      if (!event || !event.getModifierState) return;
      setCapsOn(event.getModifierState('CapsLock'));
    };

    function syncLegacyForm() {
      if (!legacyForm) return;
      const map = {
        first_name: firstName,
        last_name: lastName,
        username,
        email,
        password,
        confirm_password: confirmPassword,
        next: p.nextValue,
      };
      Object.entries(map).forEach(([name, val]) => {
        const input = legacyForm.querySelector(`[name="${name}"]`);
        if (input) input.value = val;
      });
    }

    async function handleSubmit(event) {
      event.preventDefault();

      if (!firstName || !lastName || !username || !email || !password || !confirmPassword) {
        setError('Please fill in all required fields.');
        setShakeKey((k) => k + 1);
        return;
      }
      if (password !== confirmPassword) {
        setError('Passwords must match.');
        setShakeKey((k) => k + 1);
        return;
      }

      setLoading(true);
      setError('');

      try {
        const payload = hasRecaptcha ? new FormData() : null;
        if (payload) {
          payload.append('first_name', firstName);
          payload.append('last_name', lastName);
          payload.append('username', username);
          payload.append('email', email);
          payload.append('password', password);
          payload.append('confirm_password', confirmPassword);
          payload.append('next', p.nextValue);
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
            username,
            email,
            password,
            confirm_password: confirmPassword,
            next: p.nextValue,
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
          window.location.assign(data.redirect || p.nextValue || '/dashboard/');
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
              e('h1', { className: 'auth-title' }, 'Create your account'),
              e('p', { className: 'react-subtitle' }, 'Modern, animated signup powered by React.'),
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
                  e('label', { htmlFor: 'signup-first-name' }, 'First name'),
                ]),
                e('input', {
                  id: 'signup-first-name',
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
                  e('label', { htmlFor: 'signup-last-name' }, 'Last name'),
                ]),
                e('input', {
                  id: 'signup-last-name',
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
                  e('label', { htmlFor: 'signup-username' }, 'Username'),
                ]),
                e('input', {
                  id: 'signup-username',
                  name: 'username',
                  type: 'text',
                  autoComplete: 'username',
                  placeholder: 'yourhandle',
                  value: username,
                  onChange: (evt) => setUsername(evt.target.value),
                  required: true,
                }),
              ]
            ),
            e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 4, className: 'react-field' },
              [
                e('div', { className: 'label-row' }, [
                  e('label', { htmlFor: 'signup-email' }, 'Email'),
                ]),
                e('input', {
                  id: 'signup-email',
                  name: 'email',
                  type: 'email',
                  inputMode: 'email',
                  autoComplete: 'email',
                  placeholder: 'you@example.com',
                  value: email,
                  onChange: (evt) => setEmail(evt.target.value),
                  required: true,
                }),
              ]
            ),
            e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 5, className: 'react-field' },
              [
                e('div', { className: 'label-row' }, [
                  e('label', { htmlFor: 'signup-password' }, 'Password'),
                  e('span', { className: 'micro-hint' }, 'At least 8 characters incl. upper, lower, number, special.'),
                ]),
                e('div', { className: 'react-meta' }, [
                  e('input', {
                    id: 'signup-password',
                    name: 'password',
                    type: showPassword ? 'text' : 'password',
                    autoComplete: 'new-password',
                    placeholder: '••••••••',
                    value: password,
                    onChange: (evt) => setPassword(evt.target.value),
                    onKeyDown: onCapsCheck,
                    onKeyUp: onCapsCheck,
                    required: true,
                    style: { flex: 1 },
                  }),
                  e('button', {
                    type: 'button',
                    className: 'pwd-toggle-chip',
                    onClick: () => setShowPassword((s) => !s),
                    'aria-pressed': showPassword,
                    'aria-controls': 'signup-password',
                  }, showPassword ? 'Hide' : 'Show'),
                ]),
                capsOn ? e('div', { className: 'caps-hint' }, 'Caps Lock is on') : null,
                strengthLabel ? e('div', { className: 'field-hint', style: { color: strengthColor } }, strengthLabel) : null,
              ]
            ),
            e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 6, className: 'react-field' },
              [
                e('div', { className: 'label-row' }, [
                  e('label', { htmlFor: 'signup-confirm' }, 'Confirm password'),
                ]),
                e('div', { className: 'react-meta' }, [
                  e('input', {
                    id: 'signup-confirm',
                    name: 'confirm_password',
                    type: showConfirm ? 'text' : 'password',
                    autoComplete: 'new-password',
                    placeholder: '••••••••',
                    value: confirmPassword,
                    onChange: (evt) => setConfirmPassword(evt.target.value),
                    required: true,
                    style: { flex: 1 },
                  }),
                  e('button', {
                    type: 'button',
                    className: 'pwd-toggle-chip',
                    onClick: () => setShowConfirm((s) => !s),
                    'aria-pressed': showConfirm,
                    'aria-controls': 'signup-confirm',
                  }, showConfirm ? 'Hide' : 'Show'),
                ]),
              ]
            ),
            hasRecaptcha ? e(
              motion.div,
              {
                variants: variants.item,
                initial: 'hidden',
                animate: 'show',
                custom: 7,
                className: 'g-recaptcha',
                id: 'signup-recaptcha',
                'data-sitekey': p.siteKey,
              },
              null
            ) : null,
            e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 8, className: 'terms-text' },
              [
                'By signing up you agree to our ',
                e('a', { href: p.termsUrl }, 'Terms and Conditions'),
                ' and ',
                e('a', { href: p.privacyUrl }, 'Privacy Policy'),
                '.',
              ]
            ),
            e(
              motion.button,
              {
                type: 'submit',
                className: 'submit-btn',
                disabled: loading,
                variants: variants.item,
                initial: 'hidden',
                animate: 'show',
                custom: 9,
              },
              e('span', { className: 'btn-content' }, [
                loading ? e('span', { className: 'btn-spinner', 'aria-hidden': 'true' }) : null,
                loading ? 'Creating account…' : 'Create account',
              ])
            ),
            p.googleUrl ? e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 10, className: 'oauth-block' },
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
          { variants: variants.item, initial: 'hidden', animate: 'show', custom: 11, className: 'secondary-actions' },
          [
            e('span', null, [
              'Already have an account? ',
              e('a', { className: 'link', href: p.loginUrl }, 'Log in'),
              '.',
            ]),
          ]
        ),
      ]
    );
  }

  ReactDOM.createRoot(rootEl).render(e(SignupApp, props));
})();
