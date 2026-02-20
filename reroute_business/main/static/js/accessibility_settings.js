(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var languageForm = document.getElementById("axLanguageForm");
    var preferencesForm = document.getElementById("axPreferencesForm");
    var language = document.getElementById("axLanguage");
    var lowData = document.getElementById("axLowData");

    if (!language || !lowData) {
      return;
    }

    function submitForm(formEl) {
      if (!formEl) {
        return;
      }
      if (typeof formEl.requestSubmit === "function") {
        formEl.requestSubmit();
      } else {
        formEl.submit();
      }
    }

    language.addEventListener("change", function () {
      submitForm(languageForm);
    });
    lowData.addEventListener("change", function () {
      submitForm(preferencesForm);
    });
  });
})();
