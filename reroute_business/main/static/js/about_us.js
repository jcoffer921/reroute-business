// About Us page interactions: founders carousel + smooth anchor scroll
(function () {
  const carousel = document.querySelector('[data-carousel]');
  if (!carousel) return;

  const track = carousel.querySelector('[data-carousel-track]');
  const slides = track ? Array.from(track.children) : [];
  const prevBtn = carousel.querySelector('[data-carousel-prev]');
  const nextBtn = carousel.querySelector('[data-carousel-next]');
  const dotsWrap = carousel.querySelector('[data-carousel-dots]');

  if (!track || !slides.length) return;

  let index = 0;

  const update = (nextIndex) => {
    index = (nextIndex + slides.length) % slides.length;
    track.style.transform = `translateX(${index * -100}%)`;
    slides.forEach((slide, i) => slide.setAttribute('aria-hidden', i !== index));
    if (dotsWrap) {
      Array.from(dotsWrap.children).forEach((dot, i) => {
        dot.classList.toggle('active', i === index);
        dot.setAttribute('aria-current', i === index ? 'true' : 'false');
      });
    }
  };

  if (dotsWrap) {
    dotsWrap.innerHTML = '';
    slides.forEach((_, i) => {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.setAttribute('aria-label', `Go to founder ${i + 1}`);
      dot.addEventListener('click', () => update(i));
      dotsWrap.appendChild(dot);
    });
  }

  if (prevBtn) prevBtn.addEventListener('click', () => update(index - 1));
  if (nextBtn) nextBtn.addEventListener('click', () => update(index + 1));

  update(0);
})();

(function () {
  const cta = document.querySelector('.founders-cta');
  if (!cta) return;

  cta.addEventListener('click', (event) => {
    const targetId = cta.getAttribute('href');
    if (!targetId || targetId.charAt(0) !== '#') return;
    const target = document.querySelector(targetId);
    if (!target) return;

    event.preventDefault();
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    target.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
  });
})();
