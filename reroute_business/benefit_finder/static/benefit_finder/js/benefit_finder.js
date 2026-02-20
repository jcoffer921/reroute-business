(function () {
  var STORAGE_KEY = 'reroute_benefit_finder_progress_v1';

  var QUESTIONS = [
    {
      id: 'age_range',
      prompt: 'What is your age range?',
      type: 'single',
      options: ['18–24', '25–34', '35–44', '45–54', '55–64', '65+']
    },
    {
      id: 'zip_code',
      prompt: 'What is your Philadelphia zip code?',
      type: 'zip',
      helper: 'Use this to filter reentry organizations by distance and highlight "Near you" resources later.'
    },
    {
      id: 'recently_released',
      prompt: 'Were you recently released from incarceration?',
      type: 'single',
      options: ['Yes', 'No', 'Prefer not to say']
    },
    {
      id: 'employment_status',
      prompt: 'What is your current employment status?',
      type: 'single',
      options: [
        'Employed full-time',
        'Employed part-time',
        'Unemployed, looking for work',
        'Unemployed, not looking',
        'Self-employed'
      ]
    },
    {
      id: 'housing_status',
      prompt: 'What is your current housing situation?',
      type: 'single',
      options: [
        'Stable housing',
        'Temporary/transitional',
        'Shelter',
        'Homeless/unsheltered',
        'Living with family/friends',
        'Prefer not to say'
      ]
    },
    {
      id: 'valid_id',
      prompt: 'Do you have a valid government-issued ID?',
      type: 'single',
      options: ['Yes', 'No', 'Expired', 'Not sure']
    },
    {
      id: 'childcare_need',
      prompt: 'Do you have children or need childcare?',
      type: 'single',
      options: ['Yes, I need childcare', 'Yes, but no childcare needed', 'No']
    },
    {
      id: 'transportation',
      prompt: 'How do you get around?',
      type: 'single',
      options: ['I have a car', 'Public transit (SEPTA)', 'Walk/bike', 'No reliable transportation']
    },
    {
      id: 'language_preference',
      prompt: 'What language do you prefer for services?',
      type: 'single',
      options: ['English', 'Spanish', 'Other']
    },
    {
      id: 'immediate_needs',
      prompt: 'Do you have any immediate needs right now? (Select all that apply)',
      type: 'multi',
      options: [
        'Food',
        'Housing',
        'Medical care',
        'Legal help',
        'Mental health support',
        'Job/income',
        'ID/documents',
        'None right now'
      ]
    }
  ];

  var CATEGORY_META = {
    healthcare: {
      title: 'Healthcare',
      copy: 'Find clinics and medical support services available in Philadelphia.'
    },
    mental_health: {
      title: 'Mental Health',
      copy: 'Get counseling and emotional wellness support options with trusted providers.'
    },
    job_training: {
      title: 'Job Training',
      copy: 'Explore workforce programs, resume support, and CareerLink opportunities.'
    },
    legal_aid: {
      title: 'Legal Aid',
      copy: 'Connect with legal teams that help with records, housing rights, and documentation.'
    },
    reentry_programs: {
      title: 'Reentry Programs',
      copy: 'Coordinate with reentry organizations for navigation, stabilization, and case support.'
    },
    benefits_essentials: {
      title: 'Benefits & Essentials',
      copy: 'Locate food, housing, ID, and essentials support while you stabilize.'
    }
  };

  var app = document.getElementById('benefitFinderApp');
  if (!app) {
    return;
  }

  var quizEl = document.getElementById('bfQuiz');
  var resultsEl = document.getElementById('bfResults');
  var progressCopyEl = document.getElementById('bfProgressCopy');
  var progressFillEl = document.getElementById('bfProgressFill');
  var progressBarEl = document.getElementById('bfProgressBar');
  var promptEl = document.getElementById('bfQuestionPrompt');
  var helpEl = document.getElementById('bfHelpText');
  var answerEl = document.getElementById('bfAnswerRegion');
  var validationEl = document.getElementById('bfValidation');
  var backBtn = document.getElementById('bfBackBtn');
  var nextBtn = document.getElementById('bfNextBtn');
  var saveBtn = document.getElementById('bfSaveBtn');
  var lowDataBtn = document.getElementById('bfLowDataToggle');
  var checklistEl = document.getElementById('bfChecklist');
  var categoryGridEl = document.getElementById('bfCategoryGrid');
  var downloadPrintBtn = document.getElementById('bfDownloadPrintBtn');
  var nearMeLink = document.getElementById('bfResourcesLink');
  var orgLink = document.getElementById('bfOrgLink');

  var state = {
    step: 0,
    lowDataMode: false,
    answers: {}
  };

  loadSavedState();
  render();

  backBtn.addEventListener('click', function () {
    if (state.step > 0) {
      state.step -= 1;
      hideValidation();
      render();
    }
  });

  nextBtn.addEventListener('click', function () {
    if (!canProceedFromCurrentStep()) {
      return;
    }

    if (state.step < QUESTIONS.length - 1) {
      state.step += 1;
      hideValidation();
      saveState();
      render();
      return;
    }

    saveState();
    showResults();
  });

  saveBtn.addEventListener('click', function () {
    saveState();
    saveBtn.textContent = 'Saved';
    window.setTimeout(function () {
      saveBtn.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 3v10m0 0 4-4m-4 4-4-4M5 17h14"></path></svg>Save and finish later';
    }, 1200);
  });

  lowDataBtn.addEventListener('click', function () {
    state.lowDataMode = !state.lowDataMode;
    lowDataBtn.setAttribute('aria-pressed', String(state.lowDataMode));
    app.classList.toggle('low-data-mode', state.lowDataMode);
    saveState();
  });

  downloadPrintBtn.addEventListener('click', function () {
    var plan = buildPlan(state.answers);
    var text = 'ReRoute Benefit Finder Action Plan\n\n' +
      plan.checklist.join('\n') + '\n\n' +
      'Categories: ' + plan.categories.map(function (key) { return CATEGORY_META[key].title; }).join(', ') + '\n\n' +
      'ReRoute provides guidance only and does not determine eligibility.';

    var blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var link = document.createElement('a');
    link.href = url;
    link.download = 'reroute-benefit-plan.txt';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    window.print();
  });

  function render() {
    if (state.step < 0) {
      state.step = 0;
    }

    if (state.step > QUESTIONS.length - 1) {
      state.step = QUESTIONS.length - 1;
    }

    var question = QUESTIONS[state.step];
    progressCopyEl.textContent = 'Question ' + (state.step + 1) + ' of ' + QUESTIONS.length;
    progressFillEl.style.width = String(((state.step + 1) / QUESTIONS.length) * 100) + '%';
    progressBarEl.setAttribute('aria-valuenow', String(state.step + 1));

    promptEl.textContent = question.prompt;
    helpEl.textContent = question.helper || '';
    helpEl.hidden = !question.helper;

    backBtn.disabled = state.step === 0;

    renderAnswerInput(question);
    updateNextButton();
    app.classList.toggle('low-data-mode', state.lowDataMode);
    lowDataBtn.setAttribute('aria-pressed', String(state.lowDataMode));

    quizEl.hidden = false;
    resultsEl.hidden = true;
  }

  function renderAnswerInput(question) {
    answerEl.innerHTML = '';

    if (question.type === 'zip') {
      var zipWrap = document.createElement('div');
      zipWrap.className = 'bf-zip-wrap';

      var input = document.createElement('input');
      input.type = 'text';
      input.inputMode = 'numeric';
      input.maxLength = 5;
      input.placeholder = '19104';
      input.value = state.answers[question.id] || '';
      input.setAttribute('aria-label', question.prompt);
      input.addEventListener('input', function () {
        state.answers[question.id] = input.value.replace(/\D+/g, '').slice(0, 5);
        input.value = state.answers[question.id];
        updateNextButton();
        hideValidation();
        saveState();
      });

      zipWrap.appendChild(input);
      answerEl.appendChild(zipWrap);
      input.focus();
      return;
    }

    var grid = document.createElement('div');
    grid.className = 'bf-answer-grid';

    var selected = state.answers[question.id];
    var selectedSet = new Set(Array.isArray(selected) ? selected : []);

    question.options.forEach(function (option) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'bf-choice';
      if (option.length > 18 || option === 'Prefer not to say') {
        button.classList.add('bf-choice--full');
      }

      var label = document.createElement('span');
      label.textContent = option;
      button.appendChild(label);

      var check = document.createElement('span');
      check.className = 'bf-choice__check';
      check.textContent = '✓';
      button.appendChild(check);

      var isSelected = question.type === 'multi' ? selectedSet.has(option) : selected === option;
      if (isSelected) {
        button.classList.add('is-selected');
      }

      button.addEventListener('click', function () {
        if (question.type === 'multi') {
          toggleMultiAnswer(question.id, option);
        } else {
          state.answers[question.id] = option;
        }
        hideValidation();
        saveState();
        renderAnswerInput(question);
        updateNextButton();
      });

      grid.appendChild(button);
    });

    answerEl.appendChild(grid);
  }

  function toggleMultiAnswer(questionId, option) {
    var current = state.answers[questionId];
    var values = Array.isArray(current) ? current.slice() : [];

    if (option === 'None right now') {
      state.answers[questionId] = ['None right now'];
      return;
    }

    var noneIndex = values.indexOf('None right now');
    if (noneIndex > -1) {
      values.splice(noneIndex, 1);
    }

    var index = values.indexOf(option);
    if (index > -1) {
      values.splice(index, 1);
    } else {
      values.push(option);
    }

    state.answers[questionId] = values;
  }

  function updateNextButton() {
    var question = QUESTIONS[state.step];
    var answer = state.answers[question.id];

    if (question.type === 'zip') {
      nextBtn.disabled = false;
      return;
    }

    if (question.type === 'multi') {
      nextBtn.disabled = !(Array.isArray(answer) && answer.length > 0);
      return;
    }

    nextBtn.disabled = !answer;
  }

  function canProceedFromCurrentStep() {
    var question = QUESTIONS[state.step];

    if (question.type === 'zip') {
      var zip = (state.answers[question.id] || '').trim();
      if (!/^\d{5}$/.test(zip)) {
        showValidation('Enter a valid 5-digit Philadelphia zip code to continue.');
        return false;
      }
    }

    if (question.type === 'multi') {
      var multi = state.answers[question.id];
      if (!Array.isArray(multi) || multi.length === 0) {
        showValidation('Select at least one option to continue.');
        return false;
      }
    }

    if (question.type === 'single' && !state.answers[question.id]) {
      showValidation('Select an option to continue.');
      return false;
    }

    hideValidation();
    return true;
  }

  function showValidation(message) {
    validationEl.textContent = message;
    validationEl.hidden = false;
  }

  function hideValidation() {
    validationEl.hidden = true;
    validationEl.textContent = '';
  }

  function showResults() {
    var plan = buildPlan(state.answers);

    checklistEl.innerHTML = '';
    plan.checklist.forEach(function (item) {
      var li = document.createElement('li');
      var checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.setAttribute('aria-label', item);
      var label = document.createElement('span');
      label.textContent = item;
      li.appendChild(checkbox);
      li.appendChild(label);
      checklistEl.appendChild(li);
    });

    categoryGridEl.innerHTML = '';
    plan.categories.forEach(function (categoryKey) {
      var meta = CATEGORY_META[categoryKey];
      if (!meta) {
        return;
      }
      var card = document.createElement('article');
      card.className = 'bf-category-card';

      var title = document.createElement('h4');
      title.textContent = meta.title;

      var copy = document.createElement('p');
      copy.textContent = meta.copy;

      card.appendChild(title);
      card.appendChild(copy);
      categoryGridEl.appendChild(card);
    });

    var zip = state.answers.zip_code || '';
    var lang = state.answers.language_preference || '';
    nearMeLink.href = zip ? '/resources/directory?zip=' + encodeURIComponent(zip) : '/resources/directory';
    orgLink.href = '/organizations/catalog/?zip=' + encodeURIComponent(zip) + '&language=' + encodeURIComponent(lang);

    quizEl.hidden = true;
    resultsEl.hidden = false;
    resultsEl.scrollIntoView({ behavior: state.lowDataMode ? 'auto' : 'smooth', block: 'start' });
  }

  function buildPlan(answers) {
    var tags = new Set(['navigation_support']);

    var housing = answers.housing_status;
    if (housing === 'Shelter' || housing === 'Homeless/unsheltered') {
      tags.add('emergency_housing');
      tags.add('rapid_rehousing');
      tags.add('benefits_essentials');
      tags.add('reentry_programs');
      tags.add('transportation_support');
      tags.add('housing_assistance');
    }

    if (housing === 'Temporary/transitional') {
      tags.add('rental_assistance');
      tags.add('job_training');
      tags.add('legal_aid');
      tags.add('housing_assistance');
    }

    var employment = answers.employment_status;
    if (employment === 'Unemployed, looking for work') {
      tags.add('job_training');
      tags.add('resume_support');
      tags.add('careerlink');
      tags.add('workforce_programs');
    }

    if (employment === 'Unemployed, not looking') {
      tags.add('mental_health');
      tags.add('stabilization_programs');
    }

    if (answers.recently_released === 'Yes') {
      tags.add('reentry_programs');
      tags.add('legal_aid');
      tags.add('id_assistance');
      tags.add('workforce_programs');
    }

    if (answers.valid_id === 'No' || answers.valid_id === 'Expired') {
      tags.add('id_assistance');
      tags.add('legal_aid');
      tags.add('id_checklist');
    }

    if (answers.childcare_need === 'Yes, I need childcare') {
      tags.add('childcare_support');
      tags.add('family_support');
    }

    if (answers.transportation === 'No reliable transportation') {
      tags.add('transit_assistance');
      tags.add('septa_support');
      tags.add('walkable_orgs');
      tags.add('transportation_support');
    }

    if (answers.language_preference === 'Spanish') {
      tags.add('spanish_services');
    }

    var immediateNeeds = Array.isArray(answers.immediate_needs) ? answers.immediate_needs : [];
    immediateNeeds.forEach(function (need) {
      if (need === 'Food') {
        tags.add('food_assistance');
        tags.add('benefits_essentials');
      }

      if (need === 'Housing') {
        tags.add('housing_assistance');
        tags.add('benefits_essentials');
      }

      if (need === 'Medical care') {
        tags.add('healthcare');
      }

      if (need === 'Legal help') {
        tags.add('legal_aid');
      }

      if (need === 'Mental health support') {
        tags.add('mental_health');
      }

      if (need === 'Job/income') {
        tags.add('job_training');
        tags.add('workforce_programs');
      }

      if (need === 'ID/documents') {
        tags.add('id_assistance');
        tags.add('legal_aid');
      }
    });

    if (tags.size === 1) {
      tags.add('benefits_essentials');
    }

    var checklist = buildChecklist(tags);
    var categories = buildCategories(tags);

    return {
      tags: Array.from(tags),
      checklist: checklist,
      categories: categories
    };
  }

  function buildChecklist(tags) {
    var orderedRules = [
      { tag: 'reentry_programs', item: 'Connect with a reentry program near you' },
      { tag: 'job_training', item: 'Explore job training and employment programs' },
      { tag: 'housing_assistance', item: 'Apply for housing assistance' },
      { tag: 'id_assistance', item: 'Recover or renew your government ID' },
      { tag: 'food_assistance', item: 'Access food assistance and essentials support' },
      { tag: 'healthcare', item: 'Schedule care with a clinic or healthcare provider' },
      { tag: 'mental_health', item: 'Connect with counseling or mental health support' },
      { tag: 'legal_aid', item: 'Speak with legal aid about urgent needs' },
      { tag: 'childcare_support', item: 'Review childcare subsidy and family support options' },
      { tag: 'transit_assistance', item: 'Apply for SEPTA or transportation assistance programs' },
      { tag: 'spanish_services', item: 'Request Spanish-speaking or bilingual service providers' },
      { tag: 'id_checklist', item: 'Prepare your document checklist before ID appointments' }
    ];

    var items = [];
    orderedRules.forEach(function (rule) {
      if (tags.has(rule.tag) && items.indexOf(rule.item) === -1) {
        items.push(rule.item);
      }
    });

    if (items.indexOf('Reach out for help navigating any step') === -1) {
      items.push('Reach out for help navigating any step');
    }

    return items.slice(0, 7);
  }

  function buildCategories(tags) {
    var categoryOrder = [
      { tag: 'healthcare', category: 'healthcare' },
      { tag: 'mental_health', category: 'mental_health' },
      { tag: 'job_training', category: 'job_training' },
      { tag: 'legal_aid', category: 'legal_aid' },
      { tag: 'reentry_programs', category: 'reentry_programs' },
      { tag: 'benefits_essentials', category: 'benefits_essentials' },
      { tag: 'housing_assistance', category: 'benefits_essentials' },
      { tag: 'food_assistance', category: 'benefits_essentials' },
      { tag: 'id_assistance', category: 'benefits_essentials' },
      { tag: 'childcare_support', category: 'benefits_essentials' },
      { tag: 'transit_assistance', category: 'benefits_essentials' }
    ];

    var categories = [];
    categoryOrder.forEach(function (rule) {
      if (tags.has(rule.tag) && categories.indexOf(rule.category) === -1) {
        categories.push(rule.category);
      }
    });

    if (!categories.length) {
      categories.push('benefits_essentials');
    }

    return categories;
  }

  function saveState() {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
      // Ignore storage errors for MVP.
    }
  }

  function loadSavedState() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return;
      }
      var parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== 'object') {
        return;
      }
      if (typeof parsed.step === 'number') {
        state.step = parsed.step;
      }
      if (parsed.answers && typeof parsed.answers === 'object') {
        state.answers = parsed.answers;
      }
      if (typeof parsed.lowDataMode === 'boolean') {
        state.lowDataMode = parsed.lowDataMode;
      }
    } catch (error) {
      // Ignore malformed saved state.
    }
  }
})();
