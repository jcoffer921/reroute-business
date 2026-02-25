(function () {
  var STORAGE_KEY = "reroute_last_module_url";

  function isSafeInternalUrl(rawUrl) {
    if (!rawUrl) return false;
    try {
      var resolved = new URL(rawUrl, window.location.origin);
      return resolved.origin === window.location.origin;
    } catch (_err) {
      return false;
    }
  }

  function setToast(message) {
    var toast = document.querySelector("[data-modules-toast]");
    if (!toast) return;

    toast.textContent = message;
    toast.classList.add("is-visible");
    window.clearTimeout(setToast._timerId);
    setToast._timerId = window.setTimeout(function () {
      toast.classList.remove("is-visible");
    }, 2800);
  }

  function initContinueButton() {
    var continueBtn = document.querySelector("[data-continue-module]");
    if (!continueBtn) return;

    continueBtn.addEventListener("click", function () {
      var savedUrl = "";
      try {
        savedUrl = window.localStorage.getItem(STORAGE_KEY) || "";
      } catch (_err) {
        savedUrl = "";
      }

      if (isSafeInternalUrl(savedUrl)) {
        window.location.assign(savedUrl);
        return;
      }

      var fallbackUrl = continueBtn.getAttribute("data-fallback-url") || "";
      if (isSafeInternalUrl(fallbackUrl)) {
        window.location.assign(fallbackUrl);
        return;
      }

      var grid = document.getElementById("modules-grid");
      if (grid) {
        grid.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      setToast("No saved progress yet - start with Module 1.");
    });
  }

  function trackCurrentModule() {
    var marker = document.querySelector("[data-module-watch-page]");
    if (!marker) return;

    var currentUrl = marker.getAttribute("data-current-module-url") || window.location.pathname;
    if (!isSafeInternalUrl(currentUrl)) return;

    try {
      window.localStorage.setItem(STORAGE_KEY, currentUrl);
    } catch (_err) {
      // Ignore storage failures silently (private mode, policy blocks, etc.)
    }
  }

  function initModulesFilters() {
    var form = document.querySelector("[data-modules-filter-form]");
    if (!form) return;

    form.querySelectorAll("[data-auto-submit-filter]").forEach(function (select) {
      select.addEventListener("change", function () {
        form.submit();
      });
    });
  }

  initContinueButton();
  trackCurrentModule();
  initModulesFilters();
})();
