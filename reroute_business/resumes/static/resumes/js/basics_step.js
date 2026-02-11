document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('[data-autosave-url]');
  if (!form) return;
  const autosaveUrl = form.dataset.autosaveUrl;
  const savedEl = document.querySelector('[data-saved-text]');

  const collect = () => ({
    full_name: form.querySelector('[name="full_name"]')?.value || '',
    email: form.querySelector('[name="email"]')?.value || '',
    phone: form.querySelector('[name="phone"]')?.value || '',
    city: form.querySelector('[name="city"]')?.value || '',
    state: form.querySelector('[name="state"]')?.value || '',
    headline: form.querySelector('[name="headline"]')?.value || '',
  });

  const doSave = debounce(() => {
    postJSON(autosaveUrl, collect())
      .then(() => setSavedText(savedEl, 'Saved'))
      .catch(() => {});
  }, 700);

  form.querySelectorAll('input, select').forEach((el) => {
    el.addEventListener('input', doSave);
    el.addEventListener('change', doSave);
  });
});
