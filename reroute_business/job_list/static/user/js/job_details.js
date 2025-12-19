document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('.js-apply-form');
  if (!form) return;
  form.addEventListener('submit', (e) => {
    const ok = confirm("🧠 Are you sure you want to apply for this job with your saved resume?");
    if (!ok) e.preventDefault();
  });
});
