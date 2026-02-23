(function () {
  function emitResourceEvent(eventName, details) {
    try {
      var payload = Object.assign({
        event: eventName,
        section: 'resources_home',
        timestamp: new Date().toISOString()
      }, details || {});

      if (Array.isArray(window.dataLayer)) {
        window.dataLayer.push(payload);
      }
      if (typeof window.gtag === 'function') {
        window.gtag('event', eventName, payload);
      }

      try {
        window.dispatchEvent(new CustomEvent(eventName, { detail: payload }));
      } catch (_) {
        var evt = document.createEvent('CustomEvent');
        evt.initCustomEvent(eventName, false, false, payload);
        window.dispatchEvent(evt);
      }
    } catch (_) {
      // Keep UX resilient if analytics fails
    }
  }

  function bindClickTracking() {
    var nodes = document.querySelectorAll('[data-resource-analytics]');
    nodes.forEach(function (node) {
      node.addEventListener('click', function () {
        emitResourceEvent('resources_home_click', {
          click_type: node.getAttribute('data-resource-analytics') || '',
          resource_path: node.getAttribute('data-resource-path') || '',
          resource_link: node.getAttribute('data-resource-link') || '',
          label: (node.textContent || '').trim().slice(0, 80),
          href: node.getAttribute('href') || ''
        });
      });
    });
  }

  function initGuidedPath() {
    var guidedModal = document.getElementById('guidedPathModal');
    var openGuidedButton = document.getElementById('openGuidedPath');
    var closeGuidedButton = document.getElementById('guidedPathClose');
    var progressNode = document.getElementById('guidedPathProgress');
    var resultPanel = document.getElementById('guidedPathResult');
    var resultTitleNode = document.getElementById('guidedPathResultTitle');
    var resultReasonNode = document.getElementById('guidedPathResultReason');
    var resultLinkNode = document.getElementById('guidedPathResultLink');
    var restartButton = document.getElementById('guidedPathRestart');
    var steps = Array.from(document.querySelectorAll('[data-guided-step]'));
    var optionButtons = Array.from(document.querySelectorAll('[data-guided-option]'));

    if (!guidedModal || !openGuidedButton || !steps.length) return;

    var recommendations = {
      job: {
        title: 'Job Tools',
        reason: 'This path gives you templates, interview prep, and communication tools to help you move quickly toward applications.',
        url: guidedModal.getAttribute('data-job-url') || '#'
      },
      tech: {
        title: 'Tech Courses',
        reason: 'This path matches a learning-first goal with foundations and certificate tracks you can complete at your pace.',
        url: guidedModal.getAttribute('data-tech-url') || '#'
      },
      reentry: {
        title: 'Reentry Help',
        reason: 'This path prioritizes stability support with legal aid, housing resources, and counseling services.',
        url: guidedModal.getAttribute('data-reentry-url') || '#'
      }
    };

    var state = {
      stepIndex: 0,
      answers: {},
      scores: { job: 0, tech: 0, reentry: 0 }
    };

    function resetState() {
      state.stepIndex = 0;
      state.answers = {};
      state.scores = { job: 0, tech: 0, reentry: 0 };
      if (resultPanel) resultPanel.setAttribute('hidden', '');
      steps.forEach(function (step, idx) {
        if (idx === 0) step.removeAttribute('hidden');
        else step.setAttribute('hidden', '');
      });
      if (progressNode) progressNode.textContent = 'Question 1 of 3';
    }

    function openGuidedModal() {
      resetState();
      guidedModal.removeAttribute('hidden');
      document.body.classList.add('no-scroll');
      emitResourceEvent('guided_path_opened', {});
    }

    function closeGuidedModal() {
      guidedModal.setAttribute('hidden', '');
      document.body.classList.remove('no-scroll');
    }

    function nextStep() {
      var current = steps[state.stepIndex];
      if (current) current.setAttribute('hidden', '');
      state.stepIndex += 1;
      var next = steps[state.stepIndex];
      if (next) {
        next.removeAttribute('hidden');
        if (progressNode) progressNode.textContent = 'Question ' + (state.stepIndex + 1) + ' of ' + steps.length;
      } else {
        if (progressNode) progressNode.textContent = 'Recommendation ready';
        showResult();
      }
    }

    function applyScores(button) {
      ['job', 'tech', 'reentry'].forEach(function (key) {
        var attr = button.getAttribute('data-score-' + key);
        var amount = attr ? Number(attr) : 0;
        if (!Number.isNaN(amount)) state.scores[key] += amount;
      });
    }

    function recommendedKey() {
      var entries = Object.entries(state.scores).sort(function (a, b) { return b[1] - a[1]; });
      var secondScore = entries[1] ? entries[1][1] : null;
      if (!entries.length) return 'job';
      if (entries[0][1] === secondScore) {
        var goal = state.answers.goal || '';
        if (goal === 'learn_skills') return 'tech';
        if (goal === 'stability_support') return 'reentry';
        return 'job';
      }
      return entries[0][0];
    }

    function showResult() {
      var key = recommendedKey();
      var result = recommendations[key];
      if (!result) return;

      if (resultTitleNode) resultTitleNode.textContent = result.title;
      if (resultReasonNode) resultReasonNode.textContent = result.reason;
      if (resultLinkNode) {
        resultLinkNode.setAttribute('href', result.url);
        resultLinkNode.setAttribute('data-resource-path', key + '_guided');
      }
      if (resultPanel) resultPanel.removeAttribute('hidden');

      emitResourceEvent('guided_path_completed', {
        recommended_path: key,
        answers: state.answers,
        scores: state.scores
      });
    }

    openGuidedButton.addEventListener('click', openGuidedModal);
    if (closeGuidedButton) closeGuidedButton.addEventListener('click', closeGuidedModal);
    guidedModal.addEventListener('click', function (event) {
      if (event.target && event.target.hasAttribute('data-guided-close')) closeGuidedModal();
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && !guidedModal.hasAttribute('hidden')) closeGuidedModal();
    });

    optionButtons.forEach(function (button) {
      button.addEventListener('click', function () {
        var question = button.getAttribute('data-question') || '';
        var option = button.getAttribute('data-option') || '';
        if (!question || !option) return;

        state.answers[question] = option;
        applyScores(button);
        emitResourceEvent('guided_path_answered', {
          question: question,
          option: option,
          step: state.stepIndex + 1
        });
        nextStep();
      });
    });

    if (restartButton) {
      restartButton.addEventListener('click', function () {
        emitResourceEvent('guided_path_restarted', {});
        resetState();
      });
    }
  }

  bindClickTracking();
  initGuidedPath();
})();
