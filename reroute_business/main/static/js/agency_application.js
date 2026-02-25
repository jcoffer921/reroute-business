(function () {
  var form = document.getElementById("agencyApplicationForm");
  if (!form) return;

  var steps = Array.prototype.slice.call(form.querySelectorAll(".agency-form-step"));
  var prevBtn = document.getElementById("agencyPrevStep");
  var nextBtn = document.getElementById("agencyNextStep");
  var submitBtn = document.getElementById("agencySubmitBtn");
  var currentStepLabel = document.getElementById("agencyCurrentStep");
  var progressBar = document.getElementById("agencyProgressBar");
  var stepperItems = Array.prototype.slice.call(document.querySelectorAll(".agency-stepper-item"));
  var serviceOptions = Array.prototype.slice.call(document.querySelectorAll(".agency-service-option"));
  var populationOptions = Array.prototype.slice.call(document.querySelectorAll(".agency-population-option"));
  var referralCards = Array.prototype.slice.call(document.querySelectorAll(".agency-referral-card"));
  var accuracyCheckbox = form.querySelector('input[name="accuracy_confirmation"]');
  var termsCheckbox = form.querySelector('input[name="terms_privacy_agreement"]');
  var logoInput = form.querySelector('input[type="file"][name="logo"]');
  var logoFileName = document.getElementById("agencyLogoFileName");
  var totalSteps = steps.length;
  var current = 0;
  var AUTOSAVE_KEY = "rr_agency_partnership_draft";
  var initialStepAttr = parseInt(form.getAttribute("data-initial-step") || "1", 10);
  var hasServerErrors = !!form.querySelector(".errorlist");

  function updateUI() {
    steps.forEach(function (section, idx) {
      var isActive = idx === current;
      section.hidden = !isActive;
      section.setAttribute("aria-hidden", isActive ? "false" : "true");
      section.style.display = isActive ? "block" : "none";
    });

    if (currentStepLabel) currentStepLabel.textContent = String(current + 1);
    if (progressBar) progressBar.style.width = ((current + 1) / totalSteps) * 100 + "%";
    if (prevBtn) prevBtn.disabled = current === 0;
    if (nextBtn) nextBtn.hidden = current === totalSteps - 1;
    if (submitBtn) submitBtn.hidden = current !== totalSteps - 1;
    updateSubmitAvailability();

    stepperItems.forEach(function (item, idx) {
      item.classList.remove("is-active", "is-complete");
      if (idx < current) item.classList.add("is-complete");
      else if (idx === current) item.classList.add("is-active");
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", function (event) {
      event.preventDefault();
      if (current < totalSteps - 1) {
        current += 1;
        updateUI();
        autosaveDraft();
        steps[current].scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  }

  if (prevBtn) {
    prevBtn.addEventListener("click", function (event) {
      event.preventDefault();
      if (current > 0) {
        current -= 1;
        updateUI();
        autosaveDraft();
        steps[current].scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  }

  function syncServiceSelectionUI() {
    serviceOptions.forEach(function (option) {
      var checkbox = option.querySelector('input[type="checkbox"]');
      if (!checkbox) return;
      option.classList.toggle("is-selected", checkbox.checked);
    });
  }

  function syncPopulationSelectionUI() {
    populationOptions.forEach(function (option) {
      var checkbox = option.querySelector('input[type="checkbox"]');
      if (!checkbox) return;
      option.classList.toggle("is-selected", checkbox.checked);
    });
  }

  function syncReferralSelectionUI() {
    referralCards.forEach(function (card) {
      var radio = card.querySelector('input[type="radio"]');
      if (!radio) return;
      card.classList.toggle("is-selected", radio.checked);
    });
  }

  function updateSubmitAvailability() {
    if (!submitBtn || !accuracyCheckbox || !termsCheckbox) return;
    submitBtn.disabled = !(accuracyCheckbox.checked && termsCheckbox.checked);
  }

  serviceOptions.forEach(function (option) {
    var checkbox = option.querySelector('input[type="checkbox"]');
    if (!checkbox) return;
    checkbox.addEventListener("change", syncServiceSelectionUI);
  });

  populationOptions.forEach(function (option) {
    var checkbox = option.querySelector('input[type="checkbox"]');
    if (!checkbox) return;
    checkbox.addEventListener("change", syncPopulationSelectionUI);
  });

  referralCards.forEach(function (card) {
    var radio = card.querySelector('input[type="radio"]');
    if (!radio) return;
    radio.addEventListener("change", syncReferralSelectionUI);
  });

  if (accuracyCheckbox) accuracyCheckbox.addEventListener("change", updateSubmitAvailability);
  if (termsCheckbox) termsCheckbox.addEventListener("change", updateSubmitAvailability);

  if (logoInput && logoFileName) {
    logoInput.addEventListener("change", function () {
      var file = logoInput.files && logoInput.files[0] ? logoInput.files[0].name : "";
      logoFileName.textContent = file;
    });
  }

  function autosaveDraft() {
    try {
      var payload = {};
      var checkboxCounts = {};
      var fields = form.querySelectorAll("input, select, textarea");
      fields.forEach(function (field) {
        if (field.type === "checkbox" && field.name) {
          checkboxCounts[field.name] = (checkboxCounts[field.name] || 0) + 1;
        }
      });
      fields.forEach(function (field) {
        if (!field.name || field.type === "password" || field.type === "file") return;
        if (field.type === "checkbox") {
          if ((checkboxCounts[field.name] || 0) > 1) {
            if (!payload[field.name]) payload[field.name] = [];
            if (field.checked) payload[field.name].push(field.value);
            return;
          }
          payload[field.name] = field.checked;
          return;
        }
        if (field.type === "radio") {
          if (field.checked) payload[field.name] = field.value;
          return;
        }
        payload[field.name] = field.value;
      });
      payload.__step = current;
      localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(payload));
    } catch (err) {
      return;
    }
  }

  function restoreDraft() {
    var raw;
    try {
      raw = localStorage.getItem(AUTOSAVE_KEY);
      if (!raw) return;
      var payload = JSON.parse(raw);
      var fields = form.querySelectorAll("input, select, textarea");
      fields.forEach(function (field) {
        if (!field.name || payload[field.name] === undefined) return;
        if (field.type === "checkbox") {
          if (Array.isArray(payload[field.name])) {
            field.checked = payload[field.name].indexOf(field.value) > -1;
            return;
          }
          field.checked = !!payload[field.name];
          return;
        }
        if (field.type === "radio") {
          field.checked = String(payload[field.name]) === String(field.value);
          return;
        }
        if (!field.value) field.value = payload[field.name];
      });
      if (Number.isInteger(payload.__step) && payload.__step >= 0 && payload.__step < totalSteps) {
        current = payload.__step;
      }
    } catch (err) {
      return;
    }
  }

  form.addEventListener("input", autosaveDraft);
  form.addEventListener("change", autosaveDraft);
  form.addEventListener("submit", function (event) {
    var submitter = event.submitter;
    var isFinalSubmit = submitter && submitter.name === "submit_action" && submitter.value === "submit";
    if (isFinalSubmit) {
      try {
        localStorage.removeItem(AUTOSAVE_KEY);
      } catch (err) {
        return;
      }
    } else {
      autosaveDraft();
    }
  });
  window.addEventListener("beforeunload", autosaveDraft);

  restoreDraft();
  if (hasServerErrors && Number.isInteger(initialStepAttr) && initialStepAttr >= 1 && initialStepAttr <= totalSteps) {
    current = initialStepAttr - 1;
  }
  syncServiceSelectionUI();
  syncPopulationSelectionUI();
  syncReferralSelectionUI();
  updateSubmitAvailability();
  updateUI();
})();
