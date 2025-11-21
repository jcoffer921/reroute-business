// login-react.js
// React micro-frontend for the login page with motion-driven polish

(function() {
  const rootEl = document.getElementById('login-react-root');
  if (!rootEl) return;

  const React = window.React;
  const ReactDOM = window.ReactDOM;
  const MotionLib = window.framerMotion || {};
  if (!React || !ReactDOM) return;

  const motion = MotionLib.motion || {
    div: React.forwardRef(({ children, initial, animate, exit, variants, transition, ...rest }, ref) =>
      React.createElement('div', { ...rest, ref }, children)
    ),
    form: React.forwardRef(({ children, initial, animate, exit, variants, transition, ...rest }, ref) =>
      React.createElement('form', { ...rest, ref }, children)
    ),
    button: React.forwardRef(({ children, initial, animate, exit, variants, transition, ...rest }, ref) =>
      React.createElement('button', { ...rest, ref }, children)
    ),
  };
  const AnimatePresence = MotionLib.AnimatePresence || (({ children }) => children);

  const { useEffect, useMemo, useState } = React;
  const e = React.createElement;

  function clean(v) {
    return (v === undefined || v === null || v === 'None') ? '' : v;
  }

  function getCSRFToken() {
    const m = document.cookie.match(/(?:^|;\\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function isJsonResponse(res) {
    const ct = res.headers.get('Content-Type') || '';
    return ct.includes('application/json');
  }

  function doRedirect(redirectUrl, nextValue, isEmployer) {
    const fallback = isEmployer ? '/employer/dashboard/' : '/dashboard/';
    window.location.assign(redirectUrl || nextValue || fallback);
  }

  function fallbackSubmit() {
    const legacy = document.getElementById('login-form');
    if (legacy) {
      legacy.submit();
      return;
    }
    window.location.reload();
  }

  function LoginApp(props) {
    const {
      action,
      nextValue,
      prefill,
      initialError,
      forgotUrl,
      signupUrl,
      employerUrl,
      resendUrl,
      isEmployer,
    } = props;

    const [username, setUsername] = useState(prefill);
    const [password, setPassword] = useState('');
    const [remember, setRemember] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState(initialError);
    const [loading, setLoading] = useState(false);
    const [capsOn, setCapsOn] = useState(false);
    const [shakeKey, setShakeKey] = useState(0);

    useEffect(() => {
      document.body.classList.add('login-react-active');
      return () => document.body.classList.remove('login-react-active');
    }, []);

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

    const onCapsCheck = (event) => {
      if (!event || !event.getModifierState) return;
      setCapsOn(event.getModifierState('CapsLock'));
    };

    async function handleSubmit(event) {
      event.preventDefault();

      if (!username.trim() || !password) {
        setError('Please enter your email/username and password.');
        setShakeKey((k) => k + 1);
        return;
      }

      setLoading(true);
      setError('');

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
          body: JSON.stringify({
            username,
            email: username,
            password,
            next: nextValue,
            remember,
          }),
        });

        if (!isJsonResponse(res)) {
          fallbackSubmit();
          return;
        }

        const data = await res.json().catch(() => ({}));

        if (res.ok) {
          doRedirect(data.redirect, nextValue, isEmployer);
          return;
        }

        if ([400, 401, 403].includes(res.status)) {
          setError(data.message || 'Login failed. Please try again.');
          setShakeKey((k) => k + 1);
          setLoading(false);
          return;
        }

        fallbackSubmit();
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
              e('h1', { className: 'auth-title' }, 'Login to your account'),
              e('p', { className: 'react-subtitle' }, 'Smooth, animated, and still powered by Django.'),
            ]),
          ]
        ),
        e('span', { className: 'auth-pill pill-inline', key: 'pill' }, 'Welcome back'),
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
                  e('label', { htmlFor: 'login-username-react' }, 'Email or username'),
                ]),
                e('input', {
                  id: 'login-username-react',
                  name: 'username',
                  type: 'text',
                  inputMode: 'email',
                  autoComplete: 'username',
                  placeholder: 'you@example.com',
                  value: username,
                  onChange: (evt) => setUsername(evt.target.value),
                  onKeyUp: onCapsCheck,
                  required: true,
                }),
              ]
            ),
            e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 2, className: 'react-field' },
              [
                e('div', { className: 'label-row' }, [
                  e('label', { htmlFor: 'login-password-react' }, 'Password'),
                  e('a', { className: 'micro-link', href: forgotUrl }, 'Forgot?'),
                ]),
                e('div', { className: 'react-meta' }, [
                  e('input', {
                    id: 'login-password-react',
                    name: 'password',
                    type: showPassword ? 'text' : 'password',
                    autoComplete: 'current-password',
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
                    'aria-controls': 'login-password-react',
                  }, showPassword ? 'Hide' : 'Show'),
                ]),
                capsOn ? e('div', { className: 'caps-hint' }, 'Caps Lock is on') : null,
              ]
            ),
            e(
              motion.div,
              { variants: variants.item, initial: 'hidden', animate: 'show', custom: 3, className: 'react-meta' },
              [
                e('label', { className: 'checkbox' }, [
                  e('input', {
                    type: 'checkbox',
                    name: 'remember',
                    checked: remember,
                    onChange: (evt) => setRemember(evt.target.checked),
                  }),
                  e('span', null, 'Remember this device'),
                ]),
                e('a', { className: 'micro-link', href: employerUrl }, 'Employer login'),
              ]
            ),
            e(
              motion.button,
              {
                type: 'submit',
                id: 'signin-btn-react',
                className: 'btn-pill',
                disabled: loading,
                variants: variants.item,
                initial: 'hidden',
                animate: 'show',
                custom: 4,
              },
              e('span', { className: 'btn-content' }, [
                loading ? e('span', { className: 'btn-spinner', 'aria-hidden': 'true' }) : null,
                loading ? 'Signing in…' : 'Sign in',
              ])
            ),
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
          { variants: variants.item, initial: 'hidden', animate: 'show', custom: 5, className: 'secondary-actions' },
          [
            e('span', null, [
              "Don't have an account? ",
              e('a', { className: 'link', href: signupUrl }, 'Register'),
              '.',
            ]),
            e('span', { className: 'sep', 'aria-hidden': 'true' }, '·'),
            e('a', { className: 'link', href: resendUrl }, 'Resend verification'),
          ]
        ),
      ]
    );
  }

  const props = {
    action: clean(rootEl.dataset.action) || '/login/',
    nextValue: clean(rootEl.dataset.next),
    prefill: clean(rootEl.dataset.prefill),
    initialError: clean(rootEl.dataset.error),
    forgotUrl: clean(rootEl.dataset.forgotUrl) || '#',
    signupUrl: clean(rootEl.dataset.signupUrl) || '#',
    employerUrl: clean(rootEl.dataset.employerUrl) || '#',
    resendUrl: clean(rootEl.dataset.resendUrl) || '#',
    isEmployer: (clean(rootEl.dataset.action) || '').includes('/employer/'),
  };

  ReactDOM.createRoot(rootEl).render(e(LoginApp, props));
})();
