document.addEventListener('click', (e) => {
  const link = e.target.closest('[data-close-mobile-menu]');
  if (link) {
    // call your existing toggle/close function so the menu slides out
    if (typeof toggleMobileMenu === 'function') toggleMobileMenu(false);
  }
});
