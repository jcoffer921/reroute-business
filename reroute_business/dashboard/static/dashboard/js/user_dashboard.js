if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDashboard);
} else {
  initDashboard();
}

function initDashboard() {
  initProgressRing();
  initThoughts();
  initCarousel();
}

function initProgressRing() {
  const ring = document.querySelector('.progress-ring');
  if (!ring) return;
  const value = parseInt(ring.dataset.progress || '0', 10);
  const safeValue = Number.isFinite(value) ? Math.max(0, Math.min(value, 100)) : 0;
  const label = ring.querySelector('.progress-value');

  let current = 0;
  const step = () => {
    current += 1;
    if (current > safeValue) current = safeValue;
    ring.style.setProperty('--progress', `${current}%`);
    if (label) label.textContent = `${current}%`;
    if (current < safeValue) requestAnimationFrame(step);
  };

  requestAnimationFrame(step);
}

function initThoughts() {
  const card = document.querySelector('[data-thought-card]');
  if (!card) return;

  const thoughts = [
    {
      title: 'Start with what you know',
      body: 'Your life experience is valuable. Skills like communication, leadership, and problem-solving come from many places — not just previous jobs.',
    },
    {
      title: 'Momentum wins',
      body: 'One small action a day adds up. You are building consistency and confidence with every step.',
    },
    {
      title: 'Progress is personal',
      body: 'Measure yourself by how far you have come, not how fast someone else is moving.',
    },
    {
      title: 'Keep your story close',
      body: 'Your resilience and growth are strengths. Let them lead your next conversation.',
    },
    {
      title: 'You are not alone',
      body: 'Support systems exist to help you move forward. Reach out when you are ready.',
    },
  ];

  const title = card.querySelector('[data-thought-title]');
  const text = card.querySelector('[data-thought-text]');
  const pagination = card.querySelector('[data-thought-pagination]');
  const nextBtn = card.querySelector('[data-thought-next]');
  const body = card.querySelector('[data-thought-body]');

  let index = 0;

  const render = () => {
    const item = thoughts[index];
    if (pagination) pagination.textContent = `${index + 1}/${thoughts.length}`;
    if (title) title.textContent = item.title;
    if (text) text.textContent = item.body;
  };

  const next = () => {
    if (body) body.classList.add('is-fading');
    setTimeout(() => {
      index = (index + 1) % thoughts.length;
      render();
      if (body) body.classList.remove('is-fading');
    }, 180);
  };

  render();
  if (nextBtn) nextBtn.addEventListener('click', next);
}

function initCarousel() {
  const slider = document.querySelector('[data-slider]');
  if (!slider) return;

  const track = slider.querySelector('[data-slider-track]');
  const prev = slider.querySelector('[data-slider-prev]');
  const next = slider.querySelector('[data-slider-next]');
  if (!track) return;

  const step = parseInt(slider.dataset.sliderStep || '320', 10);

  const updateButtons = () => {
    if (!prev || !next) return;
    prev.disabled = track.scrollLeft <= 0;
    next.disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 1;
  };

  if (prev) {
    prev.addEventListener('click', () => {
      track.scrollBy({ left: -step, behavior: 'smooth' });
      setTimeout(updateButtons, 250);
    });
  }

  if (next) {
    next.addEventListener('click', () => {
      track.scrollBy({ left: step, behavior: 'smooth' });
      setTimeout(updateButtons, 250);
    });
  }

  track.addEventListener('scroll', updateButtons, { passive: true });
  updateButtons();
}
