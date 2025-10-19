document.addEventListener('DOMContentLoaded', () => {
  const navbar = document.querySelector('.navbar');
  const navLinks = document.querySelector('.nav-links');
  const userBtn = document.querySelector('.user-initials-btn');
  const dropdown = document.getElementById('userDropdown');
  const arrow = document.getElementById('arrow-icon');
  let lastScrollTop = window.pageYOffset || document.documentElement.scrollTop;

  if (navbar) {
    window.addEventListener('scroll', () => {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      navbar.style.top = (scrollTop > lastScrollTop) ? '-100px' : '0';
      lastScrollTop = Math.max(scrollTop, 0);
    });

    window.addEventListener('load', () => {
      navbar.style.top = '0';
    });
  }

  // Toggle mobile menu
  const mobileToggle = document.querySelector('.mobile-menu-button');
  if (mobileToggle && navLinks) {
    mobileToggle.addEventListener('click', () => {
      navLinks.classList.toggle('show');
    });
  }

  // User menu toggle
  if (userBtn && dropdown && arrow) {
    userBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      dropdown.classList.toggle('show');
      arrow.textContent = dropdown.classList.contains('show') ? '▲' : '▼';
    });

    document.addEventListener('click', (e) => {
      if (!dropdown.contains(e.target) && !userBtn.contains(e.target)) {
        dropdown.classList.remove('show');
        arrow.textContent = '▼';
      }
    });
  }
});

setTimeout(() => {
  document.querySelectorAll('.alert').forEach(alert => {
    alert.style.display = 'none';
  });
}, 5000); // 5 seconds