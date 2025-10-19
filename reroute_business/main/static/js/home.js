/* ==========================================================
    Accessible Blog Slider
    - Arrows, dots, keyboard, swipe
    - Resizes cleanly
    - Fully commented for readability
    ========================================================== */
(function () {
  // 1) Get DOM references
  const wrapper = document.getElementById('slidesWrapper');
  if (!wrapper) return; // Safety check if markup changes

  const slides = Array.from(wrapper.querySelectorAll('.slide'));
  const dotsContainer = document.getElementById('sliderDots');
  const prevBtn = document.querySelector('.slider-btn.prev');
  const nextBtn = document.querySelector('.slider-btn.next');

  // Early exit if no slides available
  if (!slides.length) return;

  // 2) Internal state
  let index = 0;          // current slide
  let isAnimating = false;

  // 3) Set dynamic widths so each slide fills the viewport
  function setSizes() {
    const total = slides.length;
    wrapper.style.width = `${total * 100}%`;
    slides.forEach(s => { s.style.width = `${100 / total}%`; });
    goTo(index, false);   // re-apply transform after resize without animation
  }

  // 4) Build clickable dots
  function buildDots() {
    dotsContainer.innerHTML = '';
    slides.forEach((_, i) => {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.className = 'dot';
      dot.setAttribute('aria-label', `Go to slide ${i + 1}`);
      dot.addEventListener('click', () => goTo(i));
      dotsContainer.appendChild(dot);
    });
    updateDots();
  }

  // 5) Update active dot styling + aria
  function updateDots() {
    const dots = Array.from(dotsContainer.children);
    dots.forEach((d, i) => {
      d.classList.toggle('active', i === index);
      d.setAttribute('aria-current', i === index ? 'true' : 'false');
    });
  }

  // 6) Move to specific slide (with optional animation)
  function goTo(i, animate = true) {
    if (isAnimating) return;
    index = Math.max(0, Math.min(i, slides.length - 1));
    isAnimating = true;

    // Toggle CSS transition for smooth vs instant
    wrapper.style.transition = animate ? 'transform 300ms ease' : 'none';
    wrapper.style.transform = `translateX(-${index * (100 / slides.length)}%)`;

    setTimeout(() => { isAnimating = false; }, animate ? 320 : 0);
    updateDots();
  }

  // 7) Convenience next/prev
  function next() { goTo((index + 1) % slides.length); }
  function prev() { goTo((index - 1 + slides.length) % slides.length); }

  // 8) Wire up buttons
  if (prevBtn) prevBtn.addEventListener('click', prev);
  if (nextBtn) nextBtn.addEventListener('click', next);

  // 9) Keyboard navigation (make wrapper focusable)
  wrapper.setAttribute('tabindex', '0');
  wrapper.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight') next();
    if (e.key === 'ArrowLeft') prev();
  });

  // 10) Touch / swipe support
  let startX = 0, deltaX = 0;
  wrapper.addEventListener('touchstart', (e) => {
    startX = e.touches[0].clientX;
    deltaX = 0;
  }, { passive: true });

  wrapper.addEventListener('touchmove', (e) => {
    deltaX = e.touches[0].clientX - startX;
  }, { passive: true });

  wrapper.addEventListener('touchend', () => {
    // Simple threshold for swipe
    if (Math.abs(deltaX) > 50) (deltaX < 0 ? next : prev)();
  });

  // 11) Handle window resizes to keep widths correct
  window.addEventListener('resize', setSizes);

  // 12) Initialize
  setSizes();
  buildDots();

  // 13) Optional autoplay (commented out for accessibility)
  // let timer = setInterval(next, 6000);
  // wrapper.addEventListener('mouseenter', () => clearInterval(timer));
  // wrapper.addEventListener('mouseleave', () => timer = setInterval(next, 6000));
})();

// Lightweight reveal-on-scroll for testimonial pull-quote
(function () {
  const items = document.querySelectorAll('.testimonial-section .reveal-up');
  if (!items.length || !('IntersectionObserver' in window)) return;

  const obs = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.2 });

  items.forEach((el, i) => {
    // Stagger effect via transition delay
    el.style.transitionDelay = `${i * 120}ms`;
    obs.observe(el);
  });
})();
