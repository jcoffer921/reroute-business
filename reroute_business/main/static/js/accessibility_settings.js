(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("axPreferencesForm");
    var language = document.getElementById("axLanguage");
    var lowData = document.getElementById("axLowData");

    if (!form || !language || !lowData) {
      return;
    }

    function submitPreferences() {
      form.requestSubmit();
    }

    language.addEventListener("change", submitPreferences);
    lowData.addEventListener("change", submitPreferences);
  });
})();
