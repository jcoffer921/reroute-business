(function () {
  var searchInput = document.getElementById('directorySearchInput');
  var cards = Array.prototype.slice.call(document.querySelectorAll('[data-directory-card]'));
  var chipButtons = Array.prototype.slice.call(document.querySelectorAll('.directory-chip'));
  var resultMeta = document.getElementById('directoryResultsMeta');
  var noResultsEl = document.getElementById('directoryNoResults');
  var clearBtn = document.getElementById('directoryClearFilters');

  var toggleBtn = document.getElementById('directoryFilterToggle');
  var panel = document.getElementById('directoryFiltersPanel');
  var closeBtn = document.getElementById('directoryCloseFilters');
  var backdrop = document.getElementById('directoryFilterBackdrop');

  if (!cards.length) {
    return;
  }

  var selectedCategories = new Set();
  var selectedFeatures = new Set();

  chipButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      var kind = button.getAttribute('data-filter-kind');
      var value = button.getAttribute('data-filter-value');
      var targetSet = kind === 'feature' ? selectedFeatures : selectedCategories;

      if (targetSet.has(value)) {
        targetSet.delete(value);
        button.setAttribute('aria-pressed', 'false');
      } else {
        targetSet.add(value);
        button.setAttribute('aria-pressed', 'true');
      }

      applyFilters();
    });
  });

  if (searchInput) {
    searchInput.addEventListener('input', applyFilters);
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      selectedCategories.clear();
      selectedFeatures.clear();

      chipButtons.forEach(function (chip) {
        chip.setAttribute('aria-pressed', 'false');
      });

      if (searchInput) {
        searchInput.value = '';
      }

      applyFilters();
    });
  }

  if (toggleBtn && panel && backdrop) {
    toggleBtn.setAttribute('aria-expanded', 'false');
    toggleBtn.addEventListener('click', function () {
      var isOpen = panel.classList.contains('is-open');
      if (isOpen) {
        closeFilterPanel();
      } else {
        openFilterPanel();
      }
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', closeFilterPanel);
  }

  if (backdrop) {
    backdrop.addEventListener('click', closeFilterPanel);
  }

  cards.forEach(function (card) {
    card.addEventListener('click', function (event) {
      if (event.defaultPrevented) {
        return;
      }
      if (event.target.closest('a, button, input, select, textarea, label')) {
        return;
      }
      var selection = window.getSelection ? window.getSelection().toString() : '';
      if (selection) {
        return;
      }
      var cardUrl = card.getAttribute('data-card-url');
      if (cardUrl) {
        window.location.href = cardUrl;
      }
    });
  });

  window.addEventListener('resize', function () {
    if (!isMobileViewport()) {
      if (backdrop) {
        backdrop.classList.remove('show');
        backdrop.hidden = true;
      }
      return;
    }
    if (panel && !panel.classList.contains('is-open') && backdrop) {
      backdrop.classList.remove('show');
      backdrop.hidden = true;
    }
  });

  function openFilterPanel() {
    if (!panel || !toggleBtn || !backdrop) {
      return;
    }

    panel.classList.add('is-open');
    if (isMobileViewport()) {
      backdrop.hidden = false;
      backdrop.classList.add('show');
    }
    toggleBtn.setAttribute('aria-expanded', 'true');
  }

  function closeFilterPanel() {
    if (!panel || !toggleBtn || !backdrop) {
      return;
    }

    panel.classList.remove('is-open');
    if (backdrop) {
      backdrop.classList.remove('show');
      backdrop.hidden = true;
    }
    toggleBtn.setAttribute('aria-expanded', 'false');
  }

  function isMobileViewport() {
    return window.matchMedia('(max-width: 768px)').matches;
  }

  function applyFilters() {
    var term = searchInput ? searchInput.value.trim().toLowerCase() : '';
    var shownCount = 0;

    cards.forEach(function (card) {
      var categories = splitValues(card.getAttribute('data-categories'));
      var features = splitValues(card.getAttribute('data-features'));
      var haystack = (card.getAttribute('data-search') || '').toLowerCase();

      var categoryMatch = !selectedCategories.size || matchesAny(selectedCategories, categories);
      var featureMatch = !selectedFeatures.size || matchesAny(selectedFeatures, features);
      var termMatch = !term || haystack.indexOf(term) > -1;

      var isVisible = categoryMatch && featureMatch && termMatch;
      card.hidden = !isVisible;
      if (isVisible) {
        shownCount += 1;
      }
    });

    if (resultMeta) {
      resultMeta.textContent = 'Showing ' + shownCount + ' resource' + (shownCount === 1 ? '' : 's');
    }

    if (noResultsEl) {
      noResultsEl.hidden = shownCount > 0;
    }
  }

  function splitValues(raw) {
    if (!raw) {
      return [];
    }
    return raw.split('||').map(function (value) {
      return value.trim();
    }).filter(Boolean);
  }

  function matchesAny(selectedSet, values) {
    var matched = false;
    selectedSet.forEach(function (value) {
      if (values.indexOf(value) > -1) {
        matched = true;
      }
    });
    return matched;
  }
})();
