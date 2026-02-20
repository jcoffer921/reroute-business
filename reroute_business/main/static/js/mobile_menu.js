document.addEventListener('click', (e) => {
  const link = e.target.closest('[data-close-mobile-menu]');
  if (link) {
    if (typeof closeMobileMenu === 'function') {
      closeMobileMenu();
      return;
    }
    if (typeof toggleMobileMenu === 'function') toggleMobileMenu(false);
  }
});
